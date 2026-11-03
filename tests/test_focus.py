# SPDX-License-Identifier: GPL-3.0-or-later
import io
import unittest
from unittest.mock import Mock, patch
from fx240 import cli
from fx240.focus import Focus, readings, frequency, SCALE, comet_segments, draw_active_arc
from fx240.telemetry import Metric


def sample(cpu=43):
    return [Metric('ct','CPU Tctl',cpu,'C','fake'),Metric('cf','CPU policy0',4200,'MHz','fake'),
            Metric('gt','GPU edge',38,'C','fake'),Metric('gf','GPU sclk',1800,'MHz','fake')]


class FocusTests(unittest.TestCase):
    def test_comet_speed_changes_period_without_changing_frame_interval(self):
        for speed in (.25,1,3):
            theme=Focus(comet_speed=speed)
            self.assertAlmostEqual(theme.comet_time(3/speed),3)
            self.assertEqual(theme.fps,24)
        self.assertEqual(comet_segments(Focus(comet_speed=2).comet_time(.5),.5),
                         comet_segments(1,.5))
        for invalid in (0,.24,3.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):Focus(comet_speed=invalid)

    def test_live_speed_change_preserves_comet_position(self):
        old=Focus(provider=sample,comet_speed=.5)
        old(0);old(1)
        for speed in (.25,1,3):
            new=Focus(provider=sample,comet_speed=speed)
            new.inherit_motion(old,1.25)
            new.sample(1.25)
            self.assertAlmostEqual(new.comet_time(1.25),old.comet_time(1.25))
            self.assertAlmostEqual(new.arc_value(1.25),old.arc_value(1.25))
            self.assertAlmostEqual(new.comet_time(1.5)-new.comet_time(1.25),.25*speed)

    def test_accent_colors_and_rainbow_keep_numeric_readings(self):
        from fx240.focus import accent_rgb
        self.assertEqual(accent_rgb('#68B5ff'),(104,181,255))
        plain=Focus(provider=sample,accent='#68b5ff')
        rainbow=Focus(provider=sample,accent='#68b5ff',comet_style='rainbow')
        plain(0);rainbow(0)
        a=plain(1)[0];b=rainbow(1)[0]
        self.assertNotEqual(a.tobytes(),b.tobytes())
        self.assertEqual(a.crop((55,65,190,135)).tobytes(),b.crop((55,65,190,135)).tobytes())
        self.assertEqual(plain.values,rainbow.values)
        self.assertNotEqual(a.tobytes(),Focus(provider=sample)(1)[0].tobytes())
        for bad in ('blue','#fff','#12345678','#zzzzzz',None):
            with self.assertRaises(ValueError):Focus(accent=bad)
        with self.assertRaises(ValueError):Focus(comet_style='unknown')

    def test_rainbow_highlight_uses_shared_rounded_mask(self):
        from PIL import Image,ImageChops
        from fx240.focus import active_arc_mask
        for progress in (.01,.5,1):
            outside=ImageChops.invert(active_arc_mask((480,480),progress))
            for time in (.1,.8,1.5,2.8):
                image=Image.new('RGB',(480,480))
                draw_active_arc(image,time,progress,(104,181,255),'rainbow')
                self.assertIsNone(ImageChops.multiply(image.convert('L'),outside).getbbox())

    def test_fahrenheit_conversion_preserves_raw_values_and_arc(self):
        from fx240.focus import temperature
        self.assertEqual(temperature(0,1,'F'),'32.0')
        self.assertEqual(temperature(100,1,'F'),'212.0')
        self.assertEqual(temperature(-40,1,'F'),'-40.0')
        self.assertEqual(temperature(None,1,'F'),'N/A')
        c=Focus(provider=lambda:sample(50),temperature_unit='C')
        f=Focus(provider=lambda:sample(50),temperature_unit='F')
        a=c(0)[0];b=f(0)[0]
        self.assertEqual(c.values,f.values)
        self.assertEqual(c.arc_to,f.arc_to)
        self.assertNotEqual(a.tobytes(),b.tobytes())
        with self.assertRaises(ValueError):Focus(temperature_unit='K')

    def test_sampling_and_time_based_animation(self):
        provider=Mock(return_value=sample())
        theme=Focus(24,provider=provider)
        first,interval=theme(0)
        moved,_=theme(.3)
        theme(.6)
        self.assertEqual(provider.call_count,1)
        self.assertEqual(interval,1/24)
        self.assertNotEqual(first.tobytes(),moved.tobytes())
        theme(1.01)
        self.assertEqual(provider.call_count,2)

    def test_arc_continuity_on_reading_change(self):
        provider=Mock(side_effect=[sample(40),sample(80)])
        theme=Focus(provider=provider)
        theme(0);theme(.8)
        before=theme.arc_value(1.01)
        theme(1.01)
        self.assertAlmostEqual(theme.arc_value(1.01),before)
        theme(1.7)
        self.assertAlmostEqual(theme.arc_value(1.7),.8)

    def test_new_temperature_has_no_old_glyphs_on_first_changed_frame(self):
        provider=Mock(side_effect=[sample(40),sample(85)])
        theme=Focus(provider=provider,temperature_decimals=1)
        theme(0)
        changed=theme(1)[0]
        settled=Focus(provider=lambda:sample(85),temperature_decimals=1)(0)[0]
        self.assertEqual(changed.crop((55,65,190,135)).tobytes(),
                         settled.crop((55,65,190,135)).tobytes())

    def test_missing_sensor_clears_value_and_arc(self):
        provider=Mock(side_effect=[sample(),[]])
        theme=Focus(provider=provider)
        theme(0);image,_=theme(1.1)
        self.assertEqual(theme.values,(None,)*4)
        self.assertEqual(theme.arc_to,0)
        self.assertEqual(image.getpixel((0,0)),(0,0,0))

    def test_selection_units_and_nonfinite_values(self):
        self.assertEqual(readings(sample(),['ct','gf']),(43,None,None,1800))
        self.assertIsNone(readings(sample(float('nan')))[0])
        self.assertEqual(frequency(4200),'4.20 GHz')
        self.assertEqual(frequency(None),'N/A')

    def test_arc_scale_is_clamped_and_configurable(self):
        theme=Focus(provider=lambda:sample(150),arc_range=(20,80))
        theme(0)
        self.assertEqual(theme.arc_to,1)
        with self.assertRaises(ValueError): Focus(arc_range=(100,0))
        with self.assertRaises(ValueError): Focus(arc_range=(0,float('nan')))

    def test_font_fallback_and_explicit_missing_font(self):
        with patch('fx240.focus.Path.is_file',return_value=False):
            theme=Focus(provider=lambda:[])
            self.assertIsNone(theme.font_path)
            self.assertEqual(theme(0)[0].size,(240,240))
        with self.assertRaises(OSError): Focus(font_path='/nonexistent/font.ttf')

    def test_text_bounds_stay_inside_circle(self):
        from PIL import ImageDraw
        original=ImageDraw.ImageDraw.text
        boxes=[]
        def record(draw,xy,text,*args,**kwargs):
            boxes.append(draw.textbbox(xy,text,font=kwargs['font'],anchor=kwargs['anchor']))
            return original(draw,xy,text,*args,**kwargs)
        with patch.object(ImageDraw.ImageDraw,'text',record):
            for decimals in (0,1):
                Focus(provider=lambda:sample(100),temperature_decimals=decimals)(0)
                Focus(provider=lambda:sample(-10.125),temperature_decimals=decimals)(0)
            Focus(provider=lambda:sample(100),temperature_unit="F",temperature_decimals=1)(0)
            Focus(provider=lambda:[])(0)
        for left,top,right,bottom in boxes:
            for x in (left,right):
                for y in (top,bottom):
                    self.assertLessEqual((x/SCALE-119.5)**2+(y/SCALE-119.5)**2,104**2)

    def test_degree_tracks_number_width(self):
        from PIL import Image, ImageDraw
        original=ImageDraw.ImageDraw.text
        for value in (5,45,100,-10):
            boxes=[]
            def record(draw,xy,text,*args,**kwargs):
                boxes.append(draw.textbbox(xy,text,font=kwargs['font'],anchor=kwargs['anchor']))
                return original(draw,xy,text,*args,**kwargs)
            theme=Focus(provider=lambda:sample(value))
            with patch.object(ImageDraw.ImageDraw,'text',record):
                theme.draw_temperature(ImageDraw.Draw(Image.new('RGB',(480,480))),value)
            self.assertEqual(len(boxes),2)
            number,degree=boxes
            self.assertAlmostEqual((degree[0]-number[2])/SCALE,3,delta=.5)
            self.assertAlmostEqual((number[0]+degree[2])/(2*SCALE),120,delta=.5)

    def test_variable_font_weight_and_optical_size(self):
        from fx240.focus import font
        face=Mock()
        face.get_variation_axes.return_value=[
            {'name':b'Optical size','minimum':14,'default':14,'maximum':32},
            {'name':b'Weight','minimum':100,'default':400,'maximum':900}]
        with patch('fx240.typography.load_font',return_value=face):
            font('synthetic-variable-font',72,350)
        face.set_variation_by_axes.assert_called_once_with([32,350])
        font.cache_clear()
        with self.assertRaises(ValueError): Focus(font_weight=50)

    def test_comet_stays_within_temperature_arc(self):
        self.assertEqual(comet_segments(.5,0),[])
        for progress in (.01,.4,1):
            for tick in range(72):
                for left,right,color in comet_segments(tick/24,progress):
                    self.assertGreaterEqual(left,135)
                    self.assertLessEqual(right,135+270*progress+1e-9)
                    self.assertGreater(right,left)
        self.assertEqual(comet_segments(1,.4),comet_segments(4,.4))

    def test_comet_moves_with_constant_readings_without_changing_center(self):
        theme=Focus(provider=sample)
        theme(0)
        first=theme(1)[0]
        second=theme(1.5)[0]
        self.assertNotEqual(first.tobytes(),second.tobytes())
        self.assertEqual(first.crop((55,65,190,135)).tobytes(),second.crop((55,65,190,135)).tobytes())
        self.assertAlmostEqual(theme.arc_value(1.5),.43)

    def test_highlight_cannot_paint_outside_active_arc(self):
        from PIL import Image, ImageDraw, ImageChops
        from fx240.focus import active_arc_mask
        mask=active_arc_mask((480,480),.5)
        outside=ImageChops.invert(mask)
        for time in (.1,.8,1.5,2.8):
            image=Image.new('RGB',(480,480))
            draw_active_arc(image,time,.5)
            self.assertIsNone(ImageChops.multiply(image.convert('L'),outside).getbbox())

    def test_round_caps_follow_the_inward_stroke_centerline(self):
        from fx240.focus import round_arc,arc_point,ARC_BOX,ARC_WIDTH
        import math
        draw=Mock()
        round_arc(draw,135,243,'white')
        self.assertEqual(draw.ellipse.call_count,2)
        expected_radius=(ARC_BOX[2]-ARC_BOX[0]-(ARC_WIDTH-1))/2
        cx=(ARC_BOX[0]+ARC_BOX[2])/2
        cy=(ARC_BOX[1]+ARC_BOX[3])/2
        for angle,call in zip((135,243),draw.ellipse.call_args_list):
            left,top,right,bottom=call.args[0]
            self.assertAlmostEqual(right-left,ARC_WIDTH-1)
            self.assertAlmostEqual(bottom-top,ARC_WIDTH-1)
            x,y=arc_point(angle)
            self.assertAlmostEqual((left+right)/2,x)
            self.assertAlmostEqual((top+bottom)/2,y)
            self.assertAlmostEqual(math.hypot(x-cx,y-cy),expected_radius)
        draw.reset_mock()
        round_arc(draw,135,135,'white')
        draw.ellipse.assert_not_called()
        draw.arc.assert_not_called()

    def test_approved_outfit_font_is_available_by_default(self):
        from pathlib import Path
        from fx240.focus import resolve_font
        path=Path(resolve_font())
        self.assertEqual(path.name,'Outfit.ttf')
        self.assertTrue((path.parent/'OFL.txt').is_file())
        self.assertEqual(Focus().font_weight,350)

    def test_cli_focus_defaults_to_5_and_no_hardware(self):
        def play(theme,*args):
            self.assertIsInstance(theme,Focus)
            self.assertEqual(theme.fps,5)
            return []
        with patch.object(cli,'play',side_effect=play),patch('sys.stdout',new_callable=io.StringIO),patch('fx240.transport.os.open') as opened:
            cli.main(['focus','--duration','.1'])
            opened.assert_not_called()


if __name__ == '__main__': unittest.main()
