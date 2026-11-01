# SPDX-License-Identifier: GPL-3.0-or-later
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from fx240 import protocol, transport, media, telemetry, player, cli, dashboard


class ProtocolTests(unittest.TestCase):
    def test_known_vector(self):
        reports = protocol.build_reports(b'\xff\xd8abc\xff\xd9')
        expected = bytes.fromhex('435254000044524100000027b1') + bytes(19) + b'\xff\xd8abc\xff\xd9'
        self.assertEqual(reports, [expected.ljust(1024, b'\x00')])

    def test_boundaries(self):
        for size in (4, 991, 992, 993, 2016, 2017):
            jpeg = b'\xff\xd8' + bytes(size-4) + b'\xff\xd9'
            reports = protocol.build_reports(jpeg)
            raw = b''.join(reports)
            self.assertEqual(len(reports), (32+size+1023)//1024)
            self.assertEqual(int.from_bytes(raw[8:12], 'big'), size+32)
            self.assertEqual(raw[32:32+size], jpeg)
            self.assertFalse(any(raw[32+size:]))

    def test_invalid_jpeg(self):
        for data in (b'', b'hello', b'\xff\xd8bad'):
            with self.assertRaises(ValueError): protocol.build_reports(data)


class TransportTests(unittest.TestCase):
    def test_prefix_and_pauses(self):
        device = transport.Hidraw('/dev/fake'); device.fd = 12
        reports = [bytes(1024), bytes([1])*1024]
        with patch.object(transport.os, 'write', return_value=1025) as write, patch.object(transport.time, 'sleep') as sleep:
            _, times = device.send(reports)
        self.assertEqual([x.args for x in write.call_args_list], [(12,b'\x00'+r) for r in reports])
        sleep.assert_called_once_with(.01)
        self.assertEqual(len(times), 2)

    def test_partial_not_retried(self):
        device = transport.Hidraw('/dev/fake'); device.fd = 12
        with patch.object(transport.os, 'write', return_value=10) as write:
            with self.assertRaises(RuntimeError): device.send([bytes(1024)])
        self.assertEqual(write.call_count, 1)

    def test_identity_and_cleanup(self):
        for identity, accepted in (((3,0x2000,0x3000),True),((3,1,2),False),((5,0x2000,0x3000),False)):
            def ioctl(fd, code, info, mutate): info[:] = struct.pack('IHH', *identity)
            with patch.object(transport.os, 'open', return_value=12), patch.object(transport.os,'fstat') as st, patch.object(transport.stat,'S_ISCHR',return_value=True), patch.object(transport.fcntl,'ioctl',side_effect=ioctl), patch.object(transport.fcntl,'flock'), patch.object(transport.os,'close') as close:
                if accepted:
                    with transport.Hidraw('/dev/fake'): pass
                else:
                    with self.assertRaises(RuntimeError):
                        with transport.Hidraw('/dev/fake'): pass
                close.assert_called_once_with(12)

    def test_invalid_report_no_write(self):
        device = transport.Hidraw('/dev/fake'); device.fd = 12
        with patch.object(transport.os,'write') as write:
            with self.assertRaises(ValueError): device.send([b'bad'])
            write.assert_not_called()


class MediaTests(unittest.TestCase):
    def test_encode_orientation(self):
        image = Image.new('RGB',(240,240),'black')
        image.paste('red',(0,0,120,120))
        encoded = media.encode(image)
        with Image.open(io.BytesIO(encoded)) as decoded:
            self.assertEqual(decoded.size,(240,240))
            self.assertGreater(decoded.getpixel((200,200))[0],200)
            self.assertLess(decoded.getpixel((20,20))[0],10)

    def test_transparency_and_aspect(self):
        result = media.canvas(Image.new('RGBA',(100,50),(255,0,0,0)))
        self.assertEqual(result.getpixel((120,120)),(0,0,0))
        result = media.canvas(Image.new('RGB',(100,50),'white'))
        self.assertEqual(result.getpixel((120,0)),(0,0,0))
        self.assertEqual(result.getpixel((120,120)),(255,255,255))

    def test_gif_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'test.gif'
            a=Image.new('RGB',(10,10),'red'); b=Image.new('RGB',(10,10),'blue')
            a.save(path,save_all=True,append_images=[b],duration=[40,120],loop=0)
            frames=media.load(path)
            self.assertEqual([d for _,d in frames],[.04,.12])
            self.assertGreater(frames[1][0].getpixel((120,120))[2],200)


class CircularDashboardTests(unittest.TestCase):
    def test_text_boxes_fit_visible_circle(self):
        from PIL import ImageDraw
        readings = [telemetry.Metric(str(i), 'CPU ' + 'long sensor label '*10, 12345.6, 'MHz', 'fake') for i in range(4)]
        original = ImageDraw.ImageDraw.text
        boxes = []
        def record(draw, xy, text, *args, **kwargs):
            boxes.append(draw.textbbox(xy, text, font=kwargs['font']))
            return original(draw, xy, text, *args, **kwargs)
        with patch.object(ImageDraw.ImageDraw, 'text', record):
            dashboard.render(readings, [m.key for m in readings])
            dashboard.render([], ['missing sensor '*30])
            dashboard.render([])
        self.assertTrue(boxes)
        for left, top, right, bottom in boxes:
            for x in (left, right):
                for y in (top, bottom):
                    self.assertLessEqual((x-dashboard.CENTER)**2+(y-dashboard.CENTER)**2, dashboard.TEXT_RADIUS**2)

    def test_square_corners_are_black(self):
        image = dashboard.render([])
        self.assertEqual(image.size, (240,240))
        for point in ((0,0),(239,0),(0,239),(239,239)):
            self.assertEqual(image.getpixel(point),(0,0,0))


class TelemetryTests(unittest.TestCase):
    def test_dashboard_selects_cpu_gpu_temperature_frequency(self):
        readings = [telemetry.Metric(str(i), label, 1, unit, "fake")
                    for i, (label, unit) in enumerate((("GPU edge", "C"), ("GPU sclk", "MHz"),
                    ("CPU Tctl", "C"), ("CPU Tccd", "C"), ("CPU policy0", "MHz")))]
        self.assertEqual([m.key for m in dashboard.default_metrics(readings)], ["2", "4", "0", "1"])


    def test_sysfs_units_and_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            def put(path,value):
                p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
            put('class/hwmon/hwmon0/name','k10temp')
            put('class/hwmon/hwmon0/temp1_input','63500')
            put('class/hwmon/hwmon0/temp1_label','Tctl')
            put('class/hwmon/hwmon1/name','amdgpu')
            put('class/hwmon/hwmon1/freq1_input','1800000000')
            put('class/hwmon/hwmon1/temp1_input','bad')
            put('class/hwmon/hwmon2/name','unknown')
            put('class/hwmon/hwmon2/temp1_input','123')
            put('devices/system/cpu/cpufreq/policy0/scaling_cur_freq','4200000')
            values={m.key:m for m in telemetry.collect(root)}
            self.assertEqual(values['hwmon0/temp1'].value,63.5)
            self.assertIn('Tctl',values['hwmon0/temp1'].label)
            self.assertEqual(values['hwmon1/freq1'].value,1800)
            self.assertIsNone(values['hwmon1/temp1'].value)
            self.assertEqual(values['cpu/policy0'].value,4200)
            self.assertNotIn('hwmon2/temp1',values)
            put('class/hwmon/hwmon0/temp1_fault','1')
            self.assertIsNone({m.key:m for m in telemetry.collect(root)}['hwmon0/temp1'].value)

    def test_missing_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.assertEqual(telemetry.collect(root),[])
            p=root/'value';p.write_text('nan')
            self.assertIsNone(telemetry.number(p,1))


class PlayerTests(unittest.TestCase):
    def test_overload_stops_by_wall_clock(self):
        now=[0.0]
        class Slow:
            def send(self,*args):
                now[0]+=.2
                return 200,[1]
        frames=player.play(lambda t:(Image.new('RGB',(240,240)),.04),.5,Slow(),clock=lambda:now[0],sleep=lambda d:now.__setitem__(0,now[0]+d))
        self.assertEqual(len(frames),3)
        self.assertTrue(all(row['overrun_ms']>0 for row in frames))

    def test_sleep_bounded_by_duration(self):
        now = [0.0]
        rows = player.play(lambda t: (Image.new('RGB',(240,240)), 1), .05,
                           clock=lambda: now[0], sleep=lambda d: now.__setitem__(0, now[0]+d))
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(now[0],.05)

    def test_percentiles(self):
        rows=[dict(jpeg_bytes=x,reports=1,transmission_ms=0,lateness_ms=0,overrun_ms=0,write_ms=[]) for x in (0,10)]
        self.assertEqual(player.summary(rows)['jpeg_bytes']['p95'],9.5)
        self.assertNotIn('write_ms',player.summary(rows))

    def test_simulation_never_opens_hid(self):
        with patch.object(transport.os,'open') as opened, patch('sys.stdout',new_callable=io.StringIO) as out:
            cli.main(['dashboard','--duration','.001'])
            self.assertEqual(json.loads(out.getvalue())['mode'],'simulation')
            opened.assert_not_called()

    def test_send_requires_device(self):
        with patch('sys.stderr',new_callable=io.StringIO), self.assertRaises(SystemExit) as exc:
            cli.main(['dashboard','--send'])
        self.assertEqual(exc.exception.code,2)

    def test_invalid_options(self):
        for option,value in (('--fps','nan'),('--delay-ms','nan'),('--duration','inf')):
            with patch('sys.stderr',new_callable=io.StringIO), self.assertRaises(SystemExit):
                cli.main(['dashboard',option,value])

if __name__ == '__main__': unittest.main()
