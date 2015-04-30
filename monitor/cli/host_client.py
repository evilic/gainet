#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
作用：Host运行状态采集客户端
作者：王子超
邮箱：evilic@qq.com

目前想到的可以改进的地方：
提取出公共的工具类
sqlite遇到database is locked问题的完美解决
"""

#from __future__ import print_function;
#from collections import OrderedDict;
import time;
#import sys;
#import pprint;
import os;
import re;
import json;
import urllib2;

class Properties:
    # 多长时间抓取数据一次
    fetchInterval = 2;
    # 多长时间更新一次硬件信息（单位，秒）
    searchInterval = 3600;
    # 服务器配置信息
    serverUri = "http://10.160.0.108:18041";

class CpuAndMemory():
    def __init__(self):
        self.__coreNumber = self.__getCpuCoreNumber();
        self.__ts = ["", "", "", "", "", "", "", "", "", ""];
        self.__lastTenCpuRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        self.__lastTenMemRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
    def updateHw(self):
        self.__coreNumber = self.__getCpuCoreNumber();
    def __getCpuCoreNumber(self, display = False):
        """
        返回CPU的核心数量。
        """
        # 计算CPU的核心数
        cpuCore = int(os.popen('lscpu | grep "^CPU(s):"').read().replace("CPU(s):", ""));
        if display:
            print "当前电脑的CPU核心总数:", cpuCore;
        return cpuCore;
    def __getCpuAvgLoad(self, context, cpuCoreNumber = 0, display = False):
        """
        根据top的输出结果，正则出CPU的平均负载。当前不使用此方法。
        """
        cpuCore = getCpuCoreNumber() if cpuCoreNumber == 0 else cpuCoreNumber;
        # 得到该机器的1，5，15分钟CPU平均负载
        load = re.search("load average:([0-9\s\.]+),([0-9\s\.]+),([0-9\s\.]+)", context);
        # 计算1，5，15分钟的CPU平均负载（一旦超过第一个数超过100，则CPU危急）
        avg1 = float(load.group(1)) / cpuCore * 100;   # 单位是 %
        avg5 = float(load.group(2)) / cpuCore * 100;   # 单位是 %
        avg15 = float(load.group(3)) / cpuCore * 100;  # 单位是 %
        if display:
            print "经过转化的CPU平均负载(过100则CPU压力大): %f, %f, %f" % (avg1, avg5, avg15);
        return avg1, avg5, avg15;
    def __getCpuInfo(self, context):
        """
        得到CPU的相关信息，当前不使用此方法。
        """
        cpu = re.search("Cpu\(s\):([0-9\s\.]+)us,([0-9\s\.]+)sy,([0-9\s\.]+)ni,([0-9\s\.]+)id,([0-9\s\.]+)wa,([0-9\s\.]+)hi,([0-9\s\.]+)si,([0-9\s\.]+)st", context);
        return cpu;
    def __getMemInfo(self, context):
        """
        获取内存数据，当前不使用此方法。
        """
        mem = re.search("Mem :([0-9\s\.]+)total,([0-9\s\.]+)free,([0-9\s\.]+)used,([0-9\s\.]+)buff/cache", context);
        return mem;
    def __getSwapInfo(self, context):
        """
        获取交换分区数据
        """
        swap = re.search("Swap:([0-9\s\.]+)total,([0-9\s\.]+)free,([0-9\s\.]+)used.([0-9\s\.]+)avail Mem ", result);
        return swap;
    def __getCpuAndMemInfo(self, processIdsList = [1], cpuCoreNumber = 0):
        """
        返回CPU和内存的信息。
        参数可以传递过来要查看的进程PID，也可以什么都不传。
        """
        # 传过来的进程ID的数量
        processesCount = len(processIdsList);
        # 准备将传进来的进程ID拼接成字符串
        processedIdStr = "";
        for p in range(len(processIdsList)):
            processedIdStr += str(processIdsList[p]);
            if p == processesCount - 1:
                pass;
            else:
                processedIdStr += ",";
        # 准备命令行命令
        cmd = "top -bn 2 -p %s | tail -n +%d" % (processedIdStr, 9 + processesCount);
        # 调用top命令
        result = os.popen(cmd).read();
        # 命令执行结果如下：
        # top - 12:53:58 up 9 days,  2:50,  6 users,  load average: 0.27, 0.51, 0.44
        # Tasks:   2 total,   0 running,   2 sleeping,   0 stopped,   0 zombie
        # %Cpu(s):  5.2 us,  1.7 sy,  0.0 ni, 93.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
        # KiB Mem : 16269820 total,  7960612 free,  6304876 used,  2004332 buff/cache
        # KiB Swap:  4194300 total,  3850884 free,   343416 used.  8905436 avail Mem 
        #
        #   PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
        #  4900 qemu      20   0 5636772 1.871g  12316 S   6.7 12.1 151:52.95 qemu-kvm
        # 21626 qemu      20   0 5636712 360152  12268 S   6.7  2.2 601:40.48 qemu-kvm
        #print result;
        # 获取平均负载
        #print getCpuAvgLoad(result, cpuCoreNumber, True);
        # 现在的CPU使用率
        cpuRate = 100.0 - float(self.__getCpuInfo(result).group(4));
        #print "当前CPU使用率:", cpuRate;
        # 计算可用内存：未按照如下公式计算！（公式 = 第四行的free + 第四行的buffers + 第五行的cached）
        #print "物理内存共计:", float(mem.group(1)) / 1024 / 1024, "G";
        mem = self.__getMemInfo(result);
        memRate = float(mem.group(3)) / float(mem.group(1)) * 100;
        #print "物理内存使用百分比(不含SWAP):", memRate;
        ######################### 未来会加一个交换分区变化的检查。如果一直在用交换分区，则表明系统要爽了！！！！
        """
        # 以下代码实现的功能是针对每个PID显示其内存的CPU的使用情况，但是赵洋洋于2015年4月10日表明不需要其数据，故未再做维护，只保留了当时的代码。
        #print "-----------------------------------"
        start = 7;
        vms = {};
        for line in result.split("\n"):
            if start != 0:
                # 这样可以跳过前面的7行不需要的数据
                start -= 1;
            else:
                vm = [];
                i = 0;
                # 将剩余的行内数据进行处理
                for x in line.split(" "):
                    if (i == 1) and (not x == ""):
                        vm.append(x);
                    if (i == 0) and (not x == ""):
                        vms[x] = vm;
                        i = 1;
        # top -bn 1 -p 29211,21626 | tail -n +8 | awk '{print $1, $9, $10}'
        for k, v in vms.iteritems():
            print "PID", k, "占用的CPU百分比", float(v[7]) / cpuCore;
            print "PID", k, "占用的内存百分比", float(v[8]);
        #print vms;
        #print "-----------------------------------"
        """
        return cpuRate, memRate;
    def update(self):
        cpu, mem = self.__getCpuAndMemInfo();
        self.__ts = self.__ts[1:10:1] + ["%.6f" % time.time()];
        self.__lastTenCpuRecords = self.__lastTenCpuRecords[1:10:1] + [float("{0:.4f}".format(cpu))];
        self.__lastTenMemRecords = self.__lastTenMemRecords[1:10:1] + [float("{0:.4f}".format(mem))];
    def getUsage(self):
        return self.__lastTenCpuRecords, self.__ts, self.__lastTenMemRecords, self.__ts;

class Network:
    def __init__(self):
        # 初始化本机网卡
        self.__netCards = self.__getPhysicalNetCardsArray();
        self.__rx, self.__tx = self.__getNetworkInfo();
        #print self.__rx, self.__tx;
        self.__tss = time.time();
        self.__ts = ["", "", "", "", "", "", "", "", "", ""];
        self.__lastTenRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
    def updateHw(self):
        self.__netCards = self.__getPhysicalNetCardsArray();
    def __getPhysicalNetCardsArray(self, display = False):
        """
        得到物理网卡名称列表的数组形式
        """
        cards = [];
        phyDev = os.popen("ls -al /sys/class/net/ | grep -v 'virtual' | tail -n +4 | awk '{print $9}'").read();
        for x in phyDev.split("\n"):
            if x != "":
                cards.append(x);
        if display:
            print cards;
        return cards;
    def __getPhysicalNetCardsStr(self, display = False):
        """
        得到物理网卡名称列表的字符串形式。这个方法已经不再使用。
        """
        cardsArray = self.__getPhysicalNetCardsArray();
        flag = len(cardsArray) - 1;
        pointer = 0;
        result = "";
        for x in range(len(cardsArray)):
            if pointer == flag:
                result += cardsArray[x];
            else:
                result += cardsArray[x] + "\\|";
                pointer += 1;
        return result;
    def __getVirtualNetCardsArray(self, display = False):
        """
        得到虚拟网卡名称列表的数组形式。这个方法已经不再使用。
        """
        cards = [];
        virDev = os.popen("ls -al /sys/class/net/ | grep 'virtual' | tail -n +4 | awk '{print $9}'").read();
        for x in virDev.split("\n"):
            if x != "":
                cards.append(x);
        if display:
            print cards;
        return cards;
    def __getVirtualNetCardsStr(self, display = False):
        """
        得到虚拟网卡名称列表的字符串形式。这个方法已经不再使用。
        """
        virDev = os.popen("ls -al /sys/class/net/ | grep 'virtual' | tail -n +4 | awk '{print $9}'").read();
        virDevStr = "";
        countFlag = 0;       # 计数标志位
        for x in virDev.split("\n"):
            if (countFlag == 0) and (x != ""):
                virDevStr += x;
            elif (countFlag != 0) and (x != ""):
                virDevStr += "\\|" + x;
            countFlag += 1;
        if display:
            print virDevStr;
        return virDevStr;
    def __getNetworkInfo(self):
        """
        得到网卡当前的RX, TX数据
        """
        #cmd = "ifconfig -s | grep '%s' | grep -v '%s' | awk 'BEGIN {sum = 0} {sum += $3} END {print sum}'";
        cardsRxRec = [0] * len(self.__netCards);
        cardsTxRec = [0] * len(self.__netCards); 
        for i in range(len(self.__netCards)):
            cmd = "ifconfig %s 2>/dev/null | grep 'bytes' | awk '{print $5}'" % self.__netCards[i];
            #print cmd;
            recs = os.popen(cmd).read();
            recsArray = recs.split("\n");
            flag = True;
            for j in range(len(recsArray)):
                #print recsArray[j];
                if (flag) and (recsArray[j] != ""):
                    cardsRxRec[i] = float(recsArray[j]);
                    flag = False;
                elif (not flag) and (recsArray[j] != ""):
                    cardsTxRec[i] = float(recsArray[j]);
                    break;
            #print len(recsArray);
        #print cardsRxRec;
        #print cardsTxRec;
        return cardsRxRec, cardsTxRec;
    def __getNetworkSpeedInfo(self, sleepsecs = 1, display = False):
        """
        统计各个物理网卡的网速之和。这个方法已经不再使用。
        """
        # 第一次采集结果
        first = self.__getNetworkInfo();
        time.sleep(sleepsecs);
        # 第二次采集结果
        second = self.__getNetworkInfo();
        rxSpeed = 0;
        txSpeed = 0;
        for i in range(len(first[0])):
            #print (second[0][i] - first[0][i]) / 128.0 / sleepsecs;           # 单位 Kb/s
            rxSpeed += (second[0][i] - first[0][i]) / 128.0 / sleepsecs;      # 单位 Kb/s
            #print (second[1][i] - first[1][i]) / 128.0 / sleepsecs;           # 单位 Kb/s
            txSpeed += (second[1][i] - first[1][i]) / 128.0 / sleepsecs;      # 单位 Kb/s
        #print rxSpeed;
        #print txSpeed;
        return rxSpeed, txSpeed;
    def update(self):
        """
        计算网卡距离上次测量时候的平均值
        """
        # 记录当前时间
        ts = time.time();
        # 获取到最新的统计数据
        rx, tx = self.__getNetworkInfo();
        # 计算数据
        rxSpeed = 0;
        txSpeed = 0;
        for i in range(len(self.__netCards)):
            rxSpeed += (rx[i] - self.__rx[i]) / 128.0 / (ts - self.__tss);     # 单位 Kb/s
            txSpeed += (tx[i] - self.__tx[i]) / 128.0 / (ts - self.__tss);
        # 交换保存数据
        self.__rx = rx;
        self.__tx = tx;
        self.__tss = ts;
        self.__ts = self.__ts[1:10:1] + ["%.6f" % ts];
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [float("{0:.4f}".format(rxSpeed))];
    def getUsage(self):
        return self.__lastTenRecords, self.__ts;

class BlockDevices:
    def __init__(self):
        self.__devices = self.__getBlockDevices();
        self.__rw = self.__getStorageInfo();
        self.__lastTenRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        self.__tss = time.time();
        self.__ts = ["", "", "", "", "", "", "", "", "", ""];
    def updateHw(self):
        self.__devices = self.__getBlockDevices();
    def __getBlockDevices(self):
        """
        得到块存储设备名称
        """
        line = os.popen("lsblk -l | grep 'disk' | awk '{print $1}'").read().split("\n");
        result = [];
        for x in range(len(line)):
            if line[x] != "":
                result.append(line[x]);
        return result;
    def __getStorageInfo(self):
        """
        获取存储的读写次数
        """
        cmdLine = "cat ";
        for i in range(len(self.__devices)):
            cmdLine += "/sys/block/" + self.__devices[i] + "/stat "
        cmdLine += "| awk 'BEGIN {rt = 0; wt = 0} {rt += $3; wt += $7} END {print rt, wt}'";
        arr = os.popen(cmdLine).read().split(" ");
        result = [];
        for j in range(len(arr)):
            result.append(float(arr[j]));
        #print arr;
        #print len(arr);
        #print result;
        return result;
    def __getStorageSpeedInfo(self, sleepsecs = 1, display = False):
        """
        计算间隔时间内的平均磁盘读写速度，此方法现在不使用。
        """
        firstCheck = getStorageInfo();
        time.sleep(sleepsecs);
        secondCheck = getStorageInfo();
        rSpeed = (secondCheck[0] - firstCheck[0]) / sleepsecs / 2.0;
        wSpeed = (secondCheck[1] - firstCheck[1]) / sleepsecs / 2.0;
        return rSpeed, wSpeed;
    def update(self):
        ts = time.time();
        rw = self.__getStorageInfo();
        rSpeed = (rw[0] - self.__rw[0]) / 2048.0 / (ts - self.__tss);    # 单位 MB/s
        wSpeed = (rw[1] - self.__rw[1]) / 2048.0 / (ts - self.__tss);
        self.__rw = rw;
        self.__tss = ts;
        self.__ts = self.__ts[1:10:1] + ["%.6f" % ts];
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [float("{0:.4f}".format(wSpeed))];
    def getUsage(self):
        return self.__lastTenRecords, self.__ts;

class Host:
    def __init__(self):
        # 初始化主机名
        self.__hostname = self.__getHostname();
        self.__cpuAndMem = CpuAndMemory();
        self.__net = Network();
        self.__blockDevices = BlockDevices();
    def __getHostname(self, display = False):
        """
        返回主机名。
        """
        # 通过 hostname 获得主机名
        hostname = os.popen("hostname").read().strip();
        # 显示主机名
        if display:
            print "主机名:", hostname;
        return hostname;
    def getName(self):
        return self.__hostname;
    def update(self):
        self.__cpuAndMem.update();
        self.__net.update();
        self.__blockDevices.update();
    def updateHw(self):
        self.__cpuAndMem.updateHw();
        self.__net.updateHw();
        self.__blockDevices.updateHw();
    def getUsage(self):
        result = { 'name': self.getName(), 'mem': { 'data' : self.__cpuAndMem.getUsage()[2], 'time' : self.__cpuAndMem.getUsage()[3] }, 'cpu': { 'data' : self.__cpuAndMem.getUsage()[0], 'time' : self.__cpuAndMem.getUsage()[1] }, 'net': { 'data' : self.__net.getUsage()[0], 'time' : self.__net.getUsage()[1] }, 'io': { 'data' : self.__blockDevices.getUsage()[0], 'time' : self.__cpuAndMem.getUsage()[1] } };
        return json.dumps(result);
    def post(self, jsonData):
        """
        发送数据到服务端。
        """
        #print "jsonData: <START>", jsonData, "<END>";
        print "Heart beatin'...";
        req = urllib2.Request(Properties.serverUri);
        req.add_header('Content-Type', 'application/json');
        response = urllib2.urlopen(req, jsonData);
        # 发送数据到服务器，读取服务器具体响应，但是并未对响应做出处理
        html = response.read();

if __name__ == "__main__":
    """
    ############# 打印 CPU 核心信息
    CPUinfo = CPUinfo();
    for processor in CPUinfo.keys():
        print(CPUinfo[processor]["model name"]);
    # 打印最近15分钟的系统负载
    print ("loadavg", load_stat()['lavg_15']);
    ############# 打印内存信息
    meminfo = meminfo();
    print("Total memory: {0}".format(meminfo["MemTotal"]));
    print("Free memory: {0}".format(meminfo["MemFree"]));
    ############# 根据参数打印网卡信息
    if len(sys.argv) > 1:
        INTERFACE = sys.argv[1];
    else:
        INTERFACE = 'eth2'; # 目前测试环境中只有 eth2，没有 eth0
    STATS = [];
    print("Interface:", INTERFACE);
    print("In         Out");
    rx();
    tx();
    # 死循环打印网络信息
    while True:
        time.sleep(1);
        rxstat_o = list(STATS);
        rx();
        tx();
        RX = float(STATS[0]);
        RX_O = rxstat_o[0];
        TX = float(STATS[1]);
        TX_O = rxstat_o[1];
        RX_RATE = round((RX - RX_O) / 1024 / 1024, 3);
        TX_RATE = round((TX - TX_O) / 1024 / 1024, 3);
        print (RX_RATE , "MB      ", TX_RATE, "MB");
    """
    """
    test();
    net = Network();
    time.sleep(2);
    net.update();
    print net.getUsage();
    cam = CpuAndMemory();
    time.sleep(2);
    cam.update();
    print cam.getUsage();
    bd = BlockDevices();
    time.sleep(2);
    bd.update();
    print bd.getUsage();
    """
    h = Host();
    i = (Properties.searchInterval / Properties.fetchInterval) if (Properties.searchInterval / Properties.fetchInterval > 0) else 1;
    j = 0;
    while True:
        if i == j:
            j = 0;
            h.updateHw();
        j += 1;
        h.update();
        h.post(h.getUsage());
        time.sleep(Properties.fetchInterval);