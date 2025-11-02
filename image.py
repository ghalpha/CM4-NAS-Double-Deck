#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
import sys 
import time
import logging
import spidev as SPI
from gpiozero import Button
import threading
import math
import psutil
import socket
from collections import deque
from PIL import Image, ImageDraw, ImageFont

os.chdir(sys.path[0])
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from lib import LCD_2inch
from lib import Gain_Param

logging.basicConfig(level=logging.DEBUG)

# Load fonts with new paths
try:
    Font1 = ImageFont.truetype("font/Font01.ttf", 25)
    Font2 = ImageFont.truetype("font/Font01.ttf", 35)
    Font3 = ImageFont.truetype("font/Font02.ttf", 32)
except OSError as e:
    logging.error(f"Could not load fonts: {e}")
    Font1 = ImageFont.load_default()
    Font2 = ImageFont.load_default()
    Font3 = ImageFont.load_default()

User_key = 20

class image():
    flgh = True
    
    def __init__(self):
        self.gain = Gain_Param.Gain_Param()   
        self.button = Button(User_key)
        self.button.when_pressed = self.Key_Callback
        
        # Initialize smoothing buffers
        self.cpu_buffer = deque(maxlen=5)
        self.temp_buffer = deque(maxlen=3)
        self.memory_buffer = deque(maxlen=5)
        self.network_tx_buffer = deque(maxlen=3)
        self.network_rx_buffer = deque(maxlen=3)
        
        # Cache for values that don't change frequently
        self.disk_cache = {'data': None, 'timestamp': 0, 'ttl': 10}
        self.ip_cache = {'data': None, 'timestamp': 0, 'ttl': 30}
        
        # Previous network stats
        self.prev_net_stats = psutil.net_io_counters()
        self.prev_net_time = time.time()
        
        # Start background thread
        t1 = threading.Thread(target=self.gain.Hard_data, name="thread1")
        t1.daemon = True 
        t1.start()

        self.disp = LCD_2inch.LCD_2inch()
        self.temp_t = 0
        
        # Initialize display
        self.disp.Init()
        self.disp.clear()

        # Create blank image for drawing
        self.image1 = Image.new("RGB", (self.disp.height, self.disp.width), "WHITE")
        self.draw = ImageDraw.Draw(self.image1)

    def Key_Callback(self, User_key):     
        logging.info("Button pressed - future functionality to be implemented")
        pass

    def get_cached_value(self, cache_key, fetch_function):
        cache = getattr(self, f"{cache_key}_cache")
        current_time = time.time()
        
        if cache['data'] is None or (current_time - cache['timestamp']) > cache['ttl']:
            try:
                cache['data'] = fetch_function()
                cache['timestamp'] = current_time
            except Exception as e:
                logging.error(f"Error fetching {cache_key}: {e}")
                return cache['data'] if cache['data'] else "N/A"
        
        return cache['data']

    def get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect_ex(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "No Connection"

    def get_disk_usage(self):
        try:
            usage = psutil.disk_usage('/')
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            percent = (usage.used / usage.total) * 100
            return {'total': total_gb, 'used': used_gb, 'percent': percent}
        except Exception as e:
            logging.error(f"Error getting disk usage: {e}")
            return {'total': 0, 'used': 0, 'percent': 0}

    def get_smooth_cpu_usage(self):
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_buffer.append(cpu_percent)
            
            if len(self.cpu_buffer) >= 3:
                weights = [0.5, 0.3, 0.2]
                weighted_sum = sum(val * weight for val, weight in zip(list(self.cpu_buffer)[-3:], weights))
                return weighted_sum
            else:
                return sum(self.cpu_buffer) / len(self.cpu_buffer)
        except Exception as e:
            logging.error(f"Error getting CPU usage: {e}")
            return 0

    def get_smooth_memory_usage(self):
        try:
            memory = psutil.virtual_memory()
            self.memory_buffer.append(memory.percent)
            return sum(self.memory_buffer) / len(self.memory_buffer)
        except Exception as e:
            logging.error(f"Error getting memory usage: {e}")
            return 0

    def get_smooth_temperature(self):
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'rt') as f:
                temp = int(f.read()) / 1000.0
            
            self.temp_buffer.append(temp)
            smoothed_temp = sum(self.temp_buffer) / len(self.temp_buffer)
            return smoothed_temp
        except Exception as e:
            logging.error(f"Error getting temperature: {e}")
            return 0

    def get_network_speeds(self):
        try:
            current_stats = psutil.net_io_counters()
            current_time = time.time()
            
            time_delta = current_time - self.prev_net_time
            
            if time_delta > 0:
                tx_speed = (current_stats.bytes_sent - self.prev_net_stats.bytes_sent) / time_delta
                rx_speed = (current_stats.bytes_recv - self.prev_net_stats.bytes_recv) / time_delta
                
                tx_speed_kb = tx_speed / 1024
                rx_speed_kb = rx_speed / 1024
                
                self.network_tx_buffer.append(tx_speed_kb)
                self.network_rx_buffer.append(rx_speed_kb)
                
                smooth_tx = sum(self.network_tx_buffer) / len(self.network_tx_buffer)
                smooth_rx = sum(self.network_rx_buffer) / len(self.network_rx_buffer)
                
                self.prev_net_stats = current_stats
                self.prev_net_time = current_time
                
                return smooth_tx, smooth_rx
            else:
                return 0, 0
        except Exception as e:
            logging.error(f"Error getting network speeds: {e}")
            return 0, 0

    def control_fan_smooth(self, temperature):
        if temperature < 45:
            fan_speed = 0.4
        elif temperature >= 65:
            fan_speed = 1.0
        else:
            fan_speed = 0.2 + (temperature - 45) * (0.8 / 20)
        
        fan_speed = max(0.4, min(1.0, fan_speed))
        
        try:
            self.disp.FAN_PIN.value = fan_speed
        except Exception as e:
            logging.error(f"Error controlling fan: {e}")

    def format_network_speed(self, speed_kb):
        if speed_kb < 1:
            return f"{int(speed_kb * 1024)}B/s"
        elif speed_kb < 1024:
            return f"{int(speed_kb)}KB/s"
        else:
            return f"{speed_kb/1024:.1f}MB/s"

    def HMI1(self): 
        try:         
            # Load background image with fallback
            try:
                self.image = Image.open('images/BL.jpg')
            except FileNotFoundError:
                logging.warning("Background image not found, using solid background")
                self.image = Image.new("RGB", (320, 240), (0, 0, 0))
                
            self.draw = ImageDraw.Draw(self.image)
            
            # Headers - 28pt font (ORIGINAL SIZE)
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 28)
            except OSError:
                Font1 = ImageFont.load_default()
                
            self.draw.text((90, 2), 'Device Status', fill=0xf7ba47, font=Font1)

            # Labels - 15pt font (ORIGINAL SIZE)
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 15)
            except OSError:
                Font1 = ImageFont.load_default()
                
            self.draw.text((30, 141), 'CPU', fill=0xf7ba47, font=Font1)
            self.draw.text((107, 141), 'Disk', fill=0xf7ba47, font=Font1)
            self.draw.text((190, 141), 'RAM', fill=0xf7ba47, font=Font1)
            self.draw.text((267, 141), 'TEMP', fill=0xf7ba47, font=Font1)

            # Network labels - 10pt font (ORIGINAL SIZE)
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 15)
            except OSError:
                Font1 = ImageFont.load_default()
                
            self.draw.text((205, 170), 'RX', fill=0xffffff, font=Font1, stroke_width=1)  
            self.draw.text((270, 170), 'TX', fill=0xffffff, font=Font1, stroke_width=1)  

            # Time/IP - 15pt font (ORIGINAL SIZE)
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 15)
            except OSError:
                Font1 = ImageFont.load_default()
                
            time_str = time.strftime("%Y-%m-%d   %H:%M:%S", time.localtime())
            self.draw.text((5, 50), time_str, fill=0xf7ba47, font=Font1) 

            # IP Address
            ip = self.get_cached_value('ip', self.get_ip_address)
            self.draw.text((170, 50), f'IP: {ip}', fill=0xf7ba47, font=Font1) 
            
            # CPU Usage - 15pt font for percentage (ORIGINAL SIZE)
            cpu_usage = self.get_smooth_cpu_usage()
            
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 15)
            except OSError:
                Font1 = ImageFont.load_default()
            
            if cpu_usage >= 100:
                self.draw.text((27, 100), f'{int(cpu_usage)}%', fill=0xf1b400, font=Font1)
            elif cpu_usage >= 10:
                self.draw.text((30, 100), f'{int(cpu_usage)}%', fill=0xf1b400, font=Font1)
            else:
                self.draw.text((34, 100), f'{int(cpu_usage)}%', fill=0xf1b400, font=Font1)
            
            self.draw.arc((10, 80, 70, 142), 0, 360, fill=0xffffff, width=8)
            self.draw.arc((10, 80, 70, 142), -90, -90 + (cpu_usage * 360 / 100), fill=0x60ad4c, width=8)
            
            # Disk Usage - 15pt font for percentage (ORIGINAL SIZE)
            disk_info = self.get_cached_value('disk', self.get_disk_usage)
            disk_percent = disk_info['percent']
            
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 15)
            except OSError:
                Font1 = ImageFont.load_default()
            
            if disk_percent >= 100:
                self.draw.text((107, 100), f'{int(disk_percent)}%', fill=0xf1b400, font=Font1)
            elif disk_percent >= 10:
                self.draw.text((111, 100), f'{int(disk_percent)}%', fill=0xf1b400, font=Font1)
            else:
                self.draw.text((114, 100), f'{int(disk_percent)}%', fill=0xf1b400, font=Font1)
            
            self.draw.arc((90, 80, 150, 142), 0, 360, fill=0xffffff, width=8)
            self.draw.arc((90, 80, 150, 142), -90, -90 + (disk_percent * 360 / 100), fill=0x7f35e9, width=8)

            # Memory Usage - 18pt font for percentage (CORRECTED FROM ORIGINAL 15pt to match temperature style)
            memory_percent = self.get_smooth_memory_usage()
            
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 18)
            except OSError:
                Font1 = ImageFont.load_default()
            
            if memory_percent >= 100:
                self.draw.text((186, 100), f'{int(memory_percent)}%', fill=0xf1b400, font=Font1)
            elif memory_percent >= 10:
                self.draw.text((189, 100), f'{int(memory_percent)}%', fill=0xf1b400, font=Font1)
            else:
                self.draw.text((195, 100), f'{int(memory_percent)}%', fill=0xf1b400, font=Font1)
            
            self.draw.arc((173, 80, 233, 142), 0, 360, fill=0xffffff, width=8)
            self.draw.arc((173, 80, 233, 142), -90, -90 + (memory_percent * 360 / 100), fill=0xf1b400, width=8)

            # Temperature - 18pt font (ORIGINAL SIZE)
            temperature = self.get_smooth_temperature()
            self.temp_t = temperature
            self.control_fan_smooth(temperature)
            
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 18)
            except OSError:
                Font1 = ImageFont.load_default()
                
            self.draw.text((268, 100), f'{int(temperature)}C', fill=0x0088ff, font=Font1)
            
            temp_percentage = min(100, (temperature / 80) * 100)
            self.draw.arc((253, 80, 313, 142), 0, 360, fill=0xffffff, width=8)
            self.draw.arc((253, 80, 313, 142), -90, -90 + (temp_percentage * 360 / 100), fill=0x0088ff, width=8)
            
            # Network Speeds - 18pt/17pt/18pt fonts based on value (ORIGINAL VARIABLE SIZES)
            tx_speed, rx_speed = self.get_network_speeds()
            
            # TX Speed with original variable font sizing
            if tx_speed < 1:  # B/s
                try:
                    Font1 = ImageFont.truetype("font/Font02.ttf", 18)
                except OSError:
                    Font1 = ImageFont.load_default()
                tx_text = f"{int(tx_speed * 1024)}B/s"
            elif tx_speed < 1024:  # KB/s
                try:
                    Font1 = ImageFont.truetype("font/Font02.ttf", 17)
                except OSError:
                    Font1 = ImageFont.load_default()
                tx_text = f"{int(tx_speed)}KB/s"
            else:  # MB/s
                try:
                    Font1 = ImageFont.truetype("font/Font02.ttf", 18)
                except OSError:
                    Font1 = ImageFont.load_default()
                tx_text = f"{tx_speed/1024:.1f}MB/s"
            
            self.draw.text((250, 190), tx_text, fill=0x008fff, font=Font1)
            
            # RX Speed with original variable font sizing
            if rx_speed < 1:  # B/s
                try:
                    Font1 = ImageFont.truetype("font/Font02.ttf", 18)
                except OSError:
                    Font1 = ImageFont.load_default()
                rx_text = f"{int(rx_speed * 1024)}B/s"
            elif rx_speed < 1024:  # KB/s
                try:
                    Font1 = ImageFont.truetype("font/Font02.ttf", 17)
                except OSError:
                    Font1 = ImageFont.load_default()
                rx_text = f"{int(rx_speed)}KB/s"
            else:  # MB/s
                try:
                    Font1 = ImageFont.truetype("font/Font02.ttf", 18)
                except OSError:
                    Font1 = ImageFont.load_default()
                rx_text = f"{rx_speed/1024:.1f}MB/s"
            
            self.draw.text((183, 190), rx_text, fill=0x008fff, font=Font1)

            # External disk bars - 13pt font (ORIGINAL SIZE)
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 13)
            except OSError:
                Font1 = ImageFont.load_default()
                
            if self.gain.Get_back[0] == 0:
                self.draw.rectangle((40, 177, 142, 190))
                self.draw.rectangle((41, 178, 141, 189), fill=0x000000)
            else:
                self.draw.rectangle((40, 177, 142, 190))
                self.draw.rectangle((41, 178, 41 + self.gain.Get_back[2], 189), fill=0x4dff00)
                self.draw.text((80, 176), f'{int(self.gain.Get_back[2])}%', fill=0xf1b400, font=Font1)

            if self.gain.Get_back[1] == 0:
                self.draw.rectangle((40, 197, 142, 210))
                self.draw.rectangle((41, 198, 141, 209), fill=0x000000)
            else:
                self.draw.rectangle((40, 197, 142, 210))
                self.draw.rectangle((41, 198, 41 + self.gain.Get_back[3], 209), fill=0x4dff00)
                self.draw.text((80, 196), f'{int(self.gain.Get_back[3])}%', fill=0xf1b400, font=Font1)
                
            if self.gain.Get_back[4] == 1:
                try:
                    Font1 = ImageFont.truetype("font/Font02.ttf", 15)
                except OSError:
                    Font1 = ImageFont.load_default()
                self.draw.text((40, 161), 'RAID', fill=0xf7ba47, font=Font1)
            
            # Status text - 15pt font (ORIGINAL SIZE)
            try:
                Font1 = ImageFont.truetype("font/Font02.ttf", 15)
            except OSError:
                Font1 = ImageFont.load_default()
                
            if ((self.gain.Get_back[0] == 0 and self.gain.Get_back[1] == 0) or 
                (self.gain.Get_back[0] != 0 and self.gain.Get_back[1] == 0) or 
                (self.gain.Get_back[0] == 0 and self.gain.Get_back[1] != 0)):
                if self.gain.flag > 0:
                    self.draw.text((30, 210), 'Detected but not installed', fill=0xf7ba47, font=Font1)
                else:
                    self.draw.text((50, 210), 'Unpartitioned/NC', fill=0xf7ba47, font=Font1)

            # Rotate and display
            self.image = self.image.rotate(180)
            self.disp.ShowImage(self.image)
            
        except IOError as e:
            logging.info(f"IO Error in HMI1: {e}")    
        except KeyboardInterrupt:
            self.disp.module_exit()
            logging.info("Quit: Keyboard interrupt")
            exit()
        except Exception as e:
            logging.error(f"Unexpected error in HMI1: {e}")

    def HMI2(self):
        pass