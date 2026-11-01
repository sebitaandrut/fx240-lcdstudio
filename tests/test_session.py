import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from fx240.session import Settings, Snapshot, Session, find_devices
from fx240.telemetry import Metric
from fx240.focus import Focus, temperature


def metrics():
    return [Metric('ct','CPU Tctl',45.125,'C','fake'),Metric('cf','CPU policy0',3940,'MHz','fake'),
            Metric('gt','GPU edge',37.5,'C','fake'),Metric('gf','GPU sclk',1800,'MHz','fake')]


class SessionTests(unittest.TestCase):
    def capture_first_frame(self,session):
        events=[]
        original=session.publish
        def publish(event):
            events.append(event)
            original(event)
            if event['kind']=='frame':session.stop()
        session.publish=publish
        return events

    def test_preview_uses_one_sample_and_never_opens_hid(self):
        provider=Mock(return_value=metrics())
        transport=Mock()
        session=Session(Settings(),provider=provider,transport_factory=transport)
        events=self.capture_first_frame(session)
        session.run()
        transport.assert_not_called()
        provider.assert_called_once()
        frame=events[0]
        self.assertEqual(frame['metrics'],provider.return_value)
        self.assertEqual(frame['display_values'],(45.125,3940,37.5,1800))
        self.assertEqual(frame['temperature_decimals'],1)
        self.assertFalse(frame['sent'])
        self.assertEqual(frame['sequence'],1)
        self.assertEqual(frame['image'].size,(240,240))
        self.assertIsNone(session.error)
        self.assertIs(events[-1]['last_frame'],frame)

    def test_send_closes_transport_and_matches_report_sizes(self):
        device=Mock()
        device.send.return_value=(10,[.1])
        manager=Mock();manager.__enter__=Mock(return_value=device);manager.__exit__=Mock(return_value=False)
        factory=Mock(return_value=manager)
        session=Session(Settings(device='/dev/fake'),send=True,provider=metrics,transport_factory=factory)
        self.capture_first_frame(session)
        session.run()
        factory.assert_called_once_with('/dev/fake')
        manager.__exit__.assert_called_once()
        reports,delay=device.send.call_args_list[0].args
        self.assertEqual(device.send.call_count,2) # telemetry, then standby
        self.assertTrue(all(len(report)==1024 for report in reports))
        self.assertEqual(delay,2)
        self.assertEqual(session.frames,1)

    def test_failed_write_stops_and_closes_transport(self):
        device=Mock();device.send.side_effect=RuntimeError('simulated write failure')
        manager=Mock();manager.__enter__=Mock(return_value=device);manager.__exit__=Mock(return_value=False)
        session=Session(Settings(device='/dev/fake'),send=True,provider=metrics,transport_factory=lambda path:manager)
        self.capture_first_frame(session)
        session.run()
        manager.__exit__.assert_called_once()
        self.assertIn('write failure',session.output_error)
        self.assertEqual(session.events.get_nowait()['kind'],'stopped')
        self.assertEqual(session.frames,1)

    def test_stop_interrupts_wait_and_prevents_restart(self):
        session=Session(Settings(fps=1),provider=metrics)
        self.capture_first_frame(session)
        session.start();session.thread.join(2)
        self.assertFalse(session.thread.is_alive())
        self.assertEqual(session.frames,1)
        with self.assertRaises(RuntimeError):session.start()

    def test_snapshot_replaces_removed_data(self):
        provider=Mock(side_effect=[metrics(),[]])
        snapshot=Snapshot(provider)
        first=snapshot.sample();second=snapshot.sample()
        self.assertEqual(len(first),4)
        self.assertEqual(second,[])
        self.assertEqual(snapshot.sequence,2)
        self.assertTrue(snapshot.timestamp.endswith('+00:00'))

    def test_device_discovery_filters_exact_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for i,identity in enumerate(('0003:00002000:00003000','0003:0000046D:0000C092','0003:00002000:000030001')):
                node=root/f'hidraw{i}'/'device';node.mkdir(parents=True)
                (node/'uevent').write_text('HID_ID='+identity+'\n')
            self.assertEqual(find_devices(root),['/dev/hidraw0'])

    def test_settings_reject_nonfinite_delay_and_missing_device(self):
        with self.assertRaises(ValueError):Settings(accent='#fff').validate()
        with self.assertRaises(ValueError):Settings(comet_style='bad').validate()
        with self.assertRaises(ValueError):Settings(comet_speed=0).validate()
        with self.assertRaises(ValueError):Settings(comet_speed=float('nan')).validate()
        with self.assertRaises(ValueError):Settings(delay_ms=float('nan')).validate()
        with self.assertRaises(ValueError):Session(Settings(),send=True)


class DecimalTemperatureTests(unittest.TestCase):
    def test_rounding_explains_stationary_integer(self):
        self.assertEqual(temperature(44.6),'45')
        self.assertEqual(temperature(45.3),'45')
        self.assertEqual(temperature(44.6,1),'44.6')
        self.assertEqual(temperature(45.3,1),'45.3')

    def test_decimal_readout_preserves_raw_values(self):
        theme=Focus(provider=metrics,temperature_decimals=1)
        image,_=theme(0)
        self.assertEqual(theme.values[0],45.125)
        self.assertEqual(image.size,(240,240))
        with self.assertRaises(ValueError):Focus(temperature_decimals=2)


class OutputLifecycleTests(unittest.TestCase):
    def make_session(self, send=True):
        device=Mock();device.send.return_value=(1,[])
        manager=Mock();manager.__enter__=Mock(return_value=device);manager.__exit__=Mock(return_value=False)
        session=Session(Settings(device='/dev/fake'),send=send,provider=metrics,
                        transport_factory=Mock(return_value=manager))
        return session,device,manager

    def test_stop_output_keeps_preview_and_resume_reopens_transport(self):
        session,device,manager=self.make_session()
        frames=[]
        def publish(event):
            if event['kind']!='frame':return
            frames.append(event)
            if len(frames)==1:session.set_output(False)
            elif len(frames)==3:session.set_output(True)
            elif len(frames)==4:session.stop()
        session.publish=publish
        session.run()
        self.assertEqual([e['sent'] for e in frames],[True,False,False,True])
        self.assertEqual(manager.__enter__.call_count,2)
        self.assertEqual(manager.__exit__.call_count,2)
        self.assertEqual(device.send.call_count,4) # two live + two standby frames
        from fx240.media import encode
        from fx240.protocol import build_reports
        from fx240.idle import render_idle
        idle=build_reports(encode(render_idle(),65,180))
        self.assertEqual(device.send.call_args_list[1].args[0],idle)
        self.assertEqual(device.send.call_args_list[-1].args[0],idle)

    def test_suspend_sends_standby_and_resume_preserves_requested_output(self):
        import time
        session,device,manager=self.make_session()
        session.start()
        deadline=time.monotonic()+3
        while session.frames<1 and time.monotonic()<deadline:time.sleep(.01)
        session.suspend(True)
        self.assertTrue(session.output_released.wait(2))
        self.assertFalse(session.send)
        self.assertTrue(session.output_requested)
        before=session.frames
        session.suspend(False)
        while session.frames<=before and time.monotonic()<deadline:time.sleep(.01)
        session.stop();session.thread.join(2)
        self.assertFalse(session.thread.is_alive())
        self.assertEqual(manager.__enter__.call_count,2)
        self.assertEqual(manager.__exit__.call_count,2)

    def test_open_failure_keeps_preview_without_retry_loop(self):
        session,device,manager=self.make_session()
        manager.__enter__.side_effect=OSError('permission denied')
        events=[]
        def publish(event):
            events.append(event)
            if event['kind']=='frame' and event['frames']==2:session.stop()
        session.publish=publish
        session.run()
        self.assertEqual(session.frames,2)
        self.assertFalse(events[0]['sent'])
        self.assertIn('permission denied',events[0]['output_error'])
        manager.__enter__.assert_called_once()
        device.send.assert_not_called()

    def test_idle_failure_is_reported_and_transport_is_closed(self):
        session,device,manager=self.make_session()
        device.send.side_effect=[(1,[]),OSError('unplugged during standby')]
        def publish(event):
            if event['kind']=='frame':session.stop()
        session.publish=publish
        session.run()
        self.assertIn('Standby frame failed',session.output_error)
        manager.__exit__.assert_called_once()
        self.assertTrue(session.output_released.is_set())


class LiveConfigurationTests(unittest.TestCase):
    def test_live_edit_keeps_usb_open_and_rejects_invalid_font(self):
        from dataclasses import replace
        device=Mock();device.send.return_value=(1,[])
        manager=Mock();manager.__enter__=Mock(return_value=device);manager.__exit__=Mock(return_value=False)
        session=Session(Settings(device='/dev/fake'),send=True,provider=metrics,
                        transport_factory=lambda path:manager)
        events=[]
        good=replace(session.settings,font_weight=500,temperature_decimals=0,quality=75,comet_speed=2,accent="#ac8aff",comet_style="rainbow",temperature_unit="F")
        def publish(event):
            if event['kind']!='frame':return
            events.append(event)
            if len(events)==1:session.configure(good)
            elif len(events)==2:session.configure(replace(good,font_path='/missing/font.ttf'))
            elif len(events)==3:session.stop()
        session.publish=publish
        session.run()
        self.assertEqual(session.settings,good)
        self.assertEqual(session.config_revision,1)
        self.assertTrue(all(e['sent'] for e in events))
        self.assertEqual(events[1]['temperature_decimals'],0)
        self.assertEqual(events[1]['temperature_unit'],'F')
        self.assertIsNotNone(events[2]['config_error'])
        self.assertIsNone(session.error)
        self.assertEqual(device.send.call_count,4) # 3 live frames and final standby only
        manager.__enter__.assert_called_once()
        manager.__exit__.assert_called_once()

    def test_pending_edits_coalesce_and_do_not_switch_active_device(self):
        from dataclasses import replace
        session,device,manager=OutputLifecycleTests().make_session()
        events=[]
        def publish(event):
            if event['kind']!='frame':return
            events.append(event)
            if len(events)==1:
                session.configure(replace(session.settings,font_weight=400))
                session.configure(replace(session.settings,font_weight=600))
            elif len(events)==2:
                session.configure(replace(session.settings,device='/dev/other'))
            elif len(events)==3:session.stop()
        session.publish=publish
        session.run()
        self.assertEqual(session.settings.font_weight,600)
        self.assertEqual(session.settings.device,'/dev/fake')
        self.assertIn('Pause LCD output',events[2]['config_error'])
        self.assertEqual(session.config_revision,1)
        self.assertTrue(all(e['sent'] for e in events))
