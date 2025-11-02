import os
import re 
import time
import socket
import psutil

class Gain_Param():
    Get_back = [0,0,0,0,0] # Returns the memory of Disk     返回Disk的内存
    flag = 0 # Unmounted or unpartitioned   未挂载还是未分区
    def GET_IP(self):
        #会存在异常  卡死   谨慎获取  
        #There will be exceptions, get stuck, get it carefully
        #Threading is better
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect_ex(('8.8.8.8',80))
        ip=s.getsockname()[0]
        s.close()
        return ip


    def GET_Temp(self):
        with open('/sys/class/thermal/thermal_zone0/temp', 'rt') as f:
            temp = (int)(f.read() ) / 1000.0
        #print(temp)
        return temp


    def net_speed(self,interface, is_download):
        # Get the corresponding value   获取对应值
        which_num = 0 if is_download else 8

        # Read the file  读取文件
        with open('/proc/net/dev') as f:
            lines = f.readlines()
        # Get result value 获取结果值       
        for line in lines:
            if line.rstrip().split(':')[0].strip() == interface:
                return line.rstrip().split(':')[1].split()[which_num]

    def RX_speed(self):
        is_upload = True#False 
        get_time = 0.1
        
        #Gets the name of the current network card 获取当前网卡名
        interfaces = psutil.net_if_addrs()
        #Filter out the lo network card 过滤掉lo网卡
        valid_interfaces = [interface for interface in interfaces if interface != 'lo']
        # Only take the first valid interface 只取第一个有效网卡
        interface = valid_interfaces[0] if valid_interfaces else None
        
        # Computation part 计算部分
        begin = int(self.net_speed(interface, is_upload))
        time.sleep(get_time)
        end = int(self.net_speed(interface, is_upload))
        return ((end-begin) /get_time/1024)
        
    def TX_speed(self):
        is_upload = False 
        get_time = 0.1
        
        #Gets the name of the current network card 获取当前网卡名
        interfaces = psutil.net_if_addrs()
        #Filter out the lo network card 过滤掉lo网卡
        valid_interfaces = [interface for interface in interfaces if interface != 'lo']
        # Only take the first valid interface 只取第一个有效网卡
        interface = valid_interfaces[0] if valid_interfaces else None

        # Computation part 计算部分
        begin = int(self.net_speed(interface, is_upload))
        time.sleep(get_time)
        end = int(self.net_speed(interface, is_upload))

        return ((end-begin) /get_time/1024)

    def Hard_data(self):  
        while True:
            Hard_capacity1 = os.popen('lsblk  -f ').read().split('\n\n\n')[0]
            Disk_number = sum(1 for i in re.finditer(r'^[a-z]', Hard_capacity1, re.MULTILINE))
            Hard_segmentation = Hard_capacity1.split('\n\n\n')[0].split('\n')

            k = 0 # Counting migration 计数偏移
            j = 0 # Number of connection disks  连接盘的数量

            Disk0_capacity = 0   #total capacity  总容量
            Disk0_usege = 0      #have been used  已使用
            Disk1_capacity = 0
            Disk1_usege = 0
            
            for i in range(0, Disk_number):
                if(i==0):                    
                    a = Hard_segmentation[k+1].strip().split()
                    if len(a)!=1:
                        if a[1].count('raid') == 1:
                            self.Get_back[4]=1 #Checks whether RAID '1' indicates a RAID group  检测是否组RAID '1'表示组了    
                    else:
                        self.Get_back[4] = 0
                    if(a[0].count('mmcblk') == 1):
                        continue
                    name0 = a[0]  

                else :
                    a = Hard_segmentation[k+1].strip().split()
                    if(a[0].count('mmcblk') == 1):
                        continue
            
                    if len(a)!=1:
                        if a[1].count('raid') == 1:
                            self.Get_back[4] = 1  #Checks whether RAID '1' indicates a RAID group   检测是否组RAID '1'表示组了
                    else:
                        self.Get_back[4] = 0
                flgh = 0              
                
                j = j + 1
                
                if len(a)==1: 
                    disk_partition_Number = Hard_capacity1.count('─'+a[0])
                    self.Get_back[4]=0 
                else:
                    if a[1].count('raid') == 0:
                        self.Get_back[4]=0
                        disk_partition_Number = Hard_capacity1.count('─'+a[0])              
                    else:
                        disk_partition_Number = 1  
                        self.Get_back[4]=1             
                
                if(disk_partition_Number == 0):
                    disk_partition_Number = 1
                    flgh = 1               
                
                for i1 in range(0, disk_partition_Number):
                
                    if(disk_partition_Number > 0 and flgh == 0):
                        Partition_data_split = ' '.join(Hard_segmentation[i1+2+k].split()).split(' ')
                    else :
                        Partition_data_split = ' '.join(Hard_segmentation[i1+1+k].split()).split(' ')
                    if(len(Partition_data_split) <= 5 and len(Partition_data_split) > 0 ):
                        name = re.sub('[├─└]','',Partition_data_split[0])
                        if(len(Partition_data_split) == 1):
                            # print("%s The drive letter has no partition\r\n"%(name))    
                            self.flag = 0                      
                        else:
                            # print ("%s This drive letter is not mounted\n"%(name))
                            self.flag = 1 #Check whether mount disk '1' indicates no mount  检测是否挂载盘 ‘1’表示没有挂载
                        # continue
                    else:
                        # print ("%s The drive letter is properly mounted\n"%(re.sub('[├─└]','',Partition_data_split[0])))                       
                        if(disk_partition_Number > 0 and name0 == a[0] or self.Get_back[4] == 1):
                            p = os.popen("df -h "+Partition_data_split[len(Partition_data_split)-1])                          
                            i2 = 0
                            while 1:
                                i2 = i2 +1
                                line = p.readline()
                                if i2==2:
                                    Capacity = line.split()[1] #Total cost of the partition 分区总值
                                    if Capacity.count('T'):
                                        x = float(re.sub('[A-Za-z]','',Capacity)) * 1024
                                    else:
                                        x = float(re.sub('[A-Za-z]','',Capacity))
                                    Disk0_capacity = Disk0_capacity + x 

                                    # Capacity = "".join(list(filter(str.isdigit,Capacity)))
                                    
                                    Capacity_usage = line.split()[2] # Partition memory usage 分区使用内存
                                    if Capacity_usage.count('T'):
                                        x = float(re.sub('[A-Z]','',Capacity_usage)) * 1024
                                        Disk0_usege = Disk0_usege + x
                                        break
                                    elif(Capacity_usage.count('G')):
                                        x = float(re.sub('[A-Z]','',Capacity_usage))
                                        Disk0_usege = Disk0_usege + x
                                        break
                                    else:
                                        x = float(re.sub('[A-Z]','',Capacity_usage)) / 1024
                                        Disk0_usege = Disk0_usege + x
                                        break
                        else:
                            p = os.popen("df -h "+Partition_data_split[len(Partition_data_split)-1])
                            i2 = 0
                            while 1:
                                i2 = i2 +1
                                line = p.readline()
                                if i2==2:
                                    Capacity = line.split()[1] # Total cost of the partition 分区总值
                                    if Capacity.count('T'):
                                        x = float(re.sub('[A-Za-z]','',Capacity)) * 1024
                                    else:
                                        x = float(re.sub('[A-Za-z]','',Capacity))
                                    Disk1_capacity = Disk1_capacity + x

                                    Capacity_usage = line.split()[2] # Partition memory usage 分区使用内存
                                    if Capacity_usage.count('T'):
                                        x = float(re.sub('[A-Z]','',Capacity_usage)) * 1024
                                        Disk1_usege = Disk1_usege + x
                                        break
                                    elif(Capacity_usage.count('G')):
                                        x = float(re.sub('[A-Z]','',Capacity_usage))
                                        Disk1_usege = Disk1_usege + x
                                        break
                                    else:
                                        x = float(re.sub('[A-Z]','',Capacity_usage)) / 1024
                                        Disk1_usege = Disk1_usege + x
                                        break
                                       
                if(flgh == 0):
                    k = k + disk_partition_Number + 1
                else:
                    k = k + disk_partition_Number 
               
                if j == 1 and len(Partition_data_split) > 5:
                    self.flag = 0
            if self.Get_back[4] == 1:                                    
                Disk1_capacity=Disk0_capacity / 2
                Disk0_capacity=Disk1_capacity
                Disk1_usege = Disk0_usege / 2
                Disk0_usege = Disk1_usege
           
            if((Disk0_capacity == 0) and (Disk1_capacity == 0)):
                self.Get_back = [Disk0_capacity,Disk1_capacity,Disk0_usege,Disk1_usege,self.Get_back[4]]
            elif(Disk0_capacity == 0 and Disk1_capacity != 0):
                Disk1_usege = round(Disk1_usege / Disk1_capacity * 100,0)
                self.Get_back = [Disk0_capacity,Disk1_capacity,Disk0_usege,Disk1_usege,self.Get_back[4]]
            elif(Disk0_capacity != 0 and Disk1_capacity == 0):
                Disk0_usege = round(Disk0_usege / Disk0_capacity * 100,0)
                self.Get_back = [Disk0_capacity,Disk1_capacity,Disk0_usege,Disk1_usege,self.Get_back[4]]
            else:
                Disk0_usege = round(Disk0_usege / Disk0_capacity * 100,0)
                Disk1_usege = round(Disk1_usege / Disk1_capacity * 100,0)
                self.Get_back = [Disk0_capacity,Disk1_capacity,Disk0_usege,Disk1_usege,self.Get_back[4]]                     
            time.sleep(1.5)

                  
