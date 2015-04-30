#!/usr/bin/python
# -*- coding: UTF-8 -*-

import libvirt;
import time;
import json;
import urllib2;
import re;

import os;
import urllib;
import datetime;

from xml.etree import ElementTree;

class Properties:
    """
    配置参数
    """
    # 数据抓取的周期
    fetchInterval = 20;
    # 抓取延迟的周期——如果加入一台新的机器，最多花多少秒能抓取到它，此数字不能低于 interval 的值
    searchInterval = 60;
    # CloudAPI 参数配置，用于通过UUID获取到机器的名字
    openStackConfigure = ("10.160.0.108", "9000", "instance", "admin", "86e3469b0cf74186", "df24d5a1e52f4bf7a48e4a86d6553f2d");   # 格式：(ip, port, mo, admin, passwd, tenant);
    # 监控数据存储所在的节点
    serverUri = "http://10.160.0.108:18040";

class Storage:
    """
    磁盘的数据对象
    """
    def __init__(self, virtualMachine):
        self.__virtualMachine = virtualMachine;   # 对该内存信息归属的对象的引用
        self.__monitorName = "disk";              # 本监控项目的名称 ##############
        self.__lastTenRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];    # 存储最新的10个监控数据 ##############
        self.__interfaceTargetList = self.__getDisk();                                 # 获取到该虚拟机的所有存储设备
        self.__tmp_rd, self.__tmp_wr = self.__mkstart();                               # 初始化中间变量
        self.__tmp_timer = time.time();                                                # 初始化中间变量
    def __getDisk(self):
        """
        获得该虚拟机的所有存储设备，通过解析 libvirt.xml 文件
        """
        result = [];
        doc = ElementTree.parse("/var/lib/nova/instances/" + self.__virtualMachine.getUuid() + "/libvirt.xml");
        interfaces = doc.findall("./devices/disk/target");
        for i in interfaces:
            #print i.attrib["dev"];
            result += [i.attrib["dev"]];
        return result;
    def __mkstart(self):
        """
        临时数据初始化
        """
        rdSumResult = 0; # 读的数据量
        wrSumResult = 0; # 写的数据量
        for interface in self.__interfaceTargetList:
            # 针对每块存储设备，初始化首次统计结果
            rdSumResult = self.__virtualMachine.getDomain().blockStats(interface)[1];
            wrSumResult = self.__virtualMachine.getDomain().blockStats(interface)[3];
        return rdSumResult, wrSumResult;
    def getName(self): ##############
        """
        获得该监控条目的名称
        """
        return self.__monitorName;
    def update(self): ##############
        """
        更新监控信息
        """
        """
        # 方法要返回的结果
        rdSumResult = 0; # 读的数据量
        wrSumResult = 0; # 写的数据量
        # 以下数据为计算时需要
        rdFirstArray = []; # 第一次统计时的数据
        rdLastArray = [];  # 第二次统计时的数据
        wrFirstArray = []; # 第一次统计时的数据
        wrLastArray = [];  # 第二次统计时的数据
        #print self.__interfaceTargetList;
        for interface in self.__interfaceTargetList:
            # 针对每块存储设备，初始化首次统计结果
            #print self.__virtualMachine.getDomain().blockStats(interface);
            # long errs, long rd_bytes, long rd_req, long wr_bytes, long wr_req 
            rdFirstArray += [self.__virtualMachine.getDomain().blockStats(interface)[1]];
            print self.__virtualMachine.getDomain().blockStats(interface);
            #wrFirstArray += [self.__virtualMachine.getDomain().blockStats(interface)[3]];
        # 休息一秒
        time.sleep(1);
        for interface in self.__interfaceTargetList:
            # 针对每块存储设备，初始化再次统计结果
            #print self.__virtualMachine.getDomain().blockStats(interface);
            # long errs, long rd_bytes, long rd_req, long wr_bytes, long wr_req 
            rdLastArray += [self.__virtualMachine.getDomain().blockStats(interface)[1]];
            print self.__virtualMachine.getDomain().blockStats(interface);
            #wrLastArray += [self.__virtualMachine.getDomain().blockStats(interface)[3]];
        #print len(rdFirstArray);
        for i in range(len(rdFirstArray)):
            rdSumResult += float("{0:.2f}".format((rdLastArray[i] - rdFirstArray[i]) / 1.0 / 1024.0 / 1024.0));
            #wrSumResult += float("{0:.2f}".format((wrLastArray[i] - wrFirstArray[i]) / 1.0 / 1024.0 / 1024.0));
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [rdSumResult]; ##############
        """
        tmp_rd, tmp_wr = self.__mkstart();
        tmp_timer = time.time();
        # 计算硬盘读写速度
        rd_rate = float(tmp_rd - self.__tmp_rd) / (tmp_timer - self.__tmp_timer) / 1048576;    # 单位 MB/s
        wr_rate = float(tmp_wr - self.__tmp_wr) / (tmp_timer - self.__tmp_timer) / 1048576;    # 单位 MB/s
        # 更新临时数据
        self.__tmp_rd = tmp_rd;
        self.__tmp_wr = tmp_wr;
        self.__tmp_timer = tmp_timer;
        # 保存数据
        #print "读", rd_rate, "写", wr_rate;
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [float("{0:.5f}".format(wr_rate))];
    def getUsage(self): ##############
        """
        返回最近使用的10条记录给外部调用者
        """
        return self.__lastTenRecords;

class Network:
    """
    网络的数据对象
    """
    def __init__(self, virtualMachine):
        self.__virtualMachine = virtualMachine;   # 对该内存信息归属的对象的引用
        self.__monitorName = "net";            # 本监控项目的名称 ##############
        self.__lastTenRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];    # 存储最新的10个监控数据 ##############
        self.__interfaceTargetList = self.__getInterface();                            # 获取到该虚拟机的所有网络接口设备
        self.__tmp_rx, self.__tmp_tx = self.__mkstart();                               # 初始化中间变量
        self.__tmp_timer = time.time();                                                # 初始化中间变量
    def __getInterface(self):
        """
        获得该虚拟机的所有网络接口设备，通过解析 libvirt.xml 文件
        """
        result = [];
        doc = ElementTree.parse("/var/lib/nova/instances/" + self.__virtualMachine.getUuid() + "/libvirt.xml");
        interfaces = doc.findall("./devices/interface/target");
        for i in interfaces:
            #print i.attrib["dev"];
            result += [i.attrib["dev"]];
        return result;
    def __mkstart(self):
        """
        临时数据初始化
        """
        rxSumResult = 0; # 读的数据量
        txSumResult = 0; # 写的数据量
        for interface in self.__interfaceTargetList:
            # 针对每块存储设备，初始化首次统计结果
            rxSumResult = self.__virtualMachine.getDomain().interfaceStats(interface)[0];
            txSumResult = self.__virtualMachine.getDomain().interfaceStats(interface)[4];
        return rxSumResult, txSumResult;
    def getName(self): ##############
        """
        获得该监控条目的名称
        """
        return self.__monitorName;
    def update(self): ##############
        """
        更新监控信息
        """
        """
        # 方法要返回的结果
        rxSumResult = 0; # 接收到的数据量（201504071433与赵洋沟通，他不要发送出的数据包的信息）
        txSumResult = 0; # 发送出的数据量
        # 以下数据为计算时需要
        rxFirstArray = []; # 第一次统计时的数据
        rxLastArray = [];  # 第二次统计时的数据
        txFirstArray = []; # 第一次统计时的数据
        txLastArray = [];  # 第二次统计时的数据
        #print self.__interfaceTargetList;
        for interface in self.__interfaceTargetList:
            # 针对每块网卡，初始化首次统计结果
            #print self.__virtualMachine.getDomain().interfaceStats(interface);
            # rx_bytes rx_drop rx_errs rx_packets tx_bytes tx_drop tx_errs tx_packets
            rxFirstArray += [self.__virtualMachine.getDomain().interfaceStats(interface)[0]];
            #txFirstArray += [self.__virtualMachine.getDomain().interfaceStats(interface)[4]];
        # 休息一秒
        time.sleep(1);
        for interface in self.__interfaceTargetList:
            # 针对每块网卡，初始化再次统计结果
            #print self.__virtualMachine.getDomain().interfaceStats(interface);
            # rx_bytes rx_drop rx_errs rx_packets tx_bytes tx_drop tx_errs tx_packets
            rxLastArray += [self.__virtualMachine.getDomain().interfaceStats(interface)[0]];
            #txLastArray += [self.__virtualMachine.getDomain().interfaceStats(interface)[4]];
        #print len(rxFirstArray);
        for i in range(len(rxFirstArray)):
            rxSumResult += float("{0:.2f}".format((rxLastArray[i] - rxFirstArray[i]) / 1.0 / 1024.0));
            #txSumResult += float("{0:.2f}".format((txLastArray[i] - txFirstArray[i]) / 1.0 / 1024.0));
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [rxSumResult]; ##############
        """
        tmp_rx, tmp_tx = self.__mkstart();
        tmp_timer = time.time();
        # 计算网络进出速度
        rx_rate = float(tmp_rx - self.__tmp_rx) / (tmp_timer - self.__tmp_timer) / 128;    # 单位 Kbps
        tx_rate = float(tmp_tx - self.__tmp_tx) / (tmp_timer - self.__tmp_timer) / 128;    # 单位 Kbps
        # 更新临时数据
        self.__tmp_rx = tmp_rx;
        self.__tmp_tx = tmp_tx;
        self.__tmp_timer = tmp_timer;
        # 保存数据
        #print "进", rx_rate, "出", tx_rate;
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [float("{0:.4f}".format(rx_rate))];
    def getUsage(self): ##############
        """
        返回最近使用的10条记录给外部调用者
        """
        return self.__lastTenRecords;

class Memory:
    """
    内存的数据对象
    """
    def __init__(self, virtualMachine):
        self.__virtualMachine = virtualMachine;   # 对该内存信息归属的对象的引用
        self.__monitorName = "memory";            # 本监控项目的名称 ##############
        self.__lastTenRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];    # 存储最新的10个监控数据 ##############
        self.__virtualMachineInstanceId = self.__virtualMachine.getDomain().name();    # __getPid() 方法使用的数据：虚拟机的名称（举例，instance-00000006）
        #print self.__virtualMachine.getDomain().info();
        self.__virtualMachineMaxMemory = self.__virtualMachine.getDomain().info()[2];  # 该虚拟机可以用的最大的内存数，目前单位不详
    def __getMemoryM1(self, pid): ##############
        """
        获取当前已使用的内存。私有方法。
        """
        mem = 0;
        # linux下 /proc/pid(进程ID）/smaps 下保存的是进程内存映像信息，比同一目录下的maps文件更详细些
        for line in file("/proc/%d/smaps" % pid, "r"):
            if re.findall("Private_", line):
                # 统计 Private 内存信息量
                mem += int(re.findall('(\d+)', line)[0]);
        #print "mem", mem;
        return mem;
    def __getPid(self):
        """
        根据实例名获取进程ID。私有方法。
        """
        pid = (os.popen("ps aux | grep " + self.__virtualMachineInstanceId + " | grep -v 'grep' | awk '{print $2}'").readlines()[0]);
        #print "pid", pid;
        return int(pid);
    def getName(self): ##############
        """
        获得该监控条目的名称
        """
        return self.__monitorName;
    def update(self): ##############
        """
        更新监控信息
        """
        #print "haha", self.__virtualMachine.getDomain().memoryStats();
        #print "max: ", self.__virtualMachineMaxMemory;
        memusage = self.__getMemoryM1(self.__getPid()) * 100.0 / self.__virtualMachineMaxMemory;
        memusage = 100.0 if (memusage > 100.0) else memusage;                          # 设置显示的最大内存使用率为 100.0
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [float("{0:.2f}".format(memusage))]; ##############
    def getUsage(self): ##############
        """
        返回最近使用的10条记录给外部调用者
        """
        return self.__lastTenRecords;

class Cpu:
    """
    CPU 的数据信息对象，通过update()方法来更新数据，通过getUsage()方法来获取数据
    """
    def __init__(self, virtualMachine):
        self.__virtualMachine = virtualMachine;      # 对该CPU信息归属的对象的引用 ##############
        self.__lastCpuTime = self.__getCpuTime();    # 上次采集的虚拟机 CPU 运行时间，update()方法需要使用此变量
        self.__lastUpdateTime = time.time();         # 上次数据采样的实际时间，update()方法需要使用此变量
        self.__info = { "load" : "0.0" };            # 字典。最终的信息结果。（历史原因导致其存在，开始于版本一）
        self.__lastTenRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];    # 最近的10条CPU信息记录（开始于版本二） ##############
        self.__monitorName = "cpu";                  # 代码重构，新加字段，用于表示监控的条目的名称 ##############
    def __getCpuTime(self):
        """
        获得domain使用的CPU时间。私有方法。
        """
        return self.__virtualMachine.getDomain().info()[4];
    def __setCpuCount(self):
        """
        设置domain虚拟的CPU数量。私有方法。暂不使用。
        """
        self.__cpuCount = self.__virtualMachine.getDomain().info()[3];
    def __getCpuCount(self):
        """
        获得domain虚拟的CPU数量。私有方法。
        """
        # 为防止CPU数量的动态调整，所以不采取返回固定值的方式
        # return self.__cpuCount;
        return self.__virtualMachine.getDomain().info()[3];
    def getName(self): ##############
        """
        获得该监控条目的名称
        """
        return self.__monitorName;
    def update(self): ##############
        """
        更新监控信息
        """
        # 获得使用CPU的时间
        t_cpuTime = self.__getCpuTime();
        # 获得当前的更新时间
        t_updateTime = time.time();
        # 计算公式：假定两次采样的实际时间是 t1 和 t2，虚拟机 CPU 运行时间为 vt1 和 vt2，%CPU = 100% * (vt2 - vt1) / ((t2-v1) * #_of_cores * 10^9)
        result = (t_cpuTime - self.__lastCpuTime) / (t_updateTime - self.__lastUpdateTime) / self.__getCpuCount() / 10000000;
        self.__info["load"] = 100.0 if (result > 100.0) else result;                          # 设置显示的最大CPU使用率为 100.0
        self.__info["load"] = 0.0 if (self.__info["load"] < 0.0) else self.__info["load"];    # 设置显示的最小CPU使用率为 0.0
        # 将此次的计算数据记录下来，以下次更新时使用
        self.__lastCpuTime = t_cpuTime;
        self.__lastUpdateTime = t_updateTime;
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [float("{0:.2f}".format(self.__info["load"]))]; ##############
    def getUsage(self): ##############
        """
        返回最近使用的10条记录给外部调用者
        """
        #if self.__info["load"] == 0.0:
        #    time.sleep(1);
        #    self.update();
        #return float("{0:.2f}".format(self.__info["load"]));
        # 下面的代码已被移至update()方法体内
        #self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [float("{0:.2f}".format(self.__info["load"]))];
        return self.__lastTenRecords;

class AnalysisTimestamp:
    """
    时间戳对象
    """
    def __init__(self, virtualMachine):
        self.__virtualMachine = virtualMachine; # 对该时间戳信息归属的对象的引用
        self.__monitorName = "time";            # 本监控项目的名称 ##############
        #self.__lastTenRecords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];  # 存储最新的10个监控时间点 ##############
        self.__lastTenRecords = ["", "", "", "", "", "", "", "", "", ""];  # 存储最新的10个监控时间点 ##############
    def getName(self): ##############
        """
        获得该监控条目的名称
        """
        return self.__monitorName;
    def update(self): ##############
        """
        更新监控信息
        """
        #self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [time.time()];
        #self.__lastTenRecords = self.__lastTenRecords[1:10:1] + [str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))];
        self.__lastTenRecords = self.__lastTenRecords[1:10:1] + ["%.6f" % time.time()];
    def getUsage(self): ##############
        """
        返回最近使用的10条记录给外部调用者
        """
        return self.__lastTenRecords;

class VirtualMachine:
    """
    虚拟机对象
    """  
    def __init__(self, domain):
        self.__domain = domain;                                  # 存储虚拟机的 domain 对象
        self.__uuid = self.__domain.UUIDString();                # 存储虚拟机的 UUID 信息
        self.__name = self.__getNameByUuid(self.getUuid());
        self.__info = {};                                        # 存储虚拟机的所有监控数据（字典）
        self.__cpu = Cpu(self);                                  # 新建CPU信息对象
        self.__info[self.__cpu.getName()] = self.__cpu;
        self.__ts = AnalysisTimestamp(self);                     # 新建时间戳对象
        self.__info[self.__ts.getName()] = self.__ts;
        self.__mem = Memory(self);                               # 新建内存监控对象
        self.__info[self.__mem.getName()] = self.__mem;
        self.__net = Network(self);                              # 新建网络监控对象
        self.__info[self.__net.getName()] = self.__net;
        self.__disk = Storage(self);                             # 新建存储监控对象
        self.__info[self.__disk.getName()] = self.__disk;
    def getDomain(self):
        """
        返回该虚拟机对象的 domain 对象，以方便其它对象直接调用 libvirt 的 api。
        """
        return self.__domain;
    def getUuid(self):
        """
        返回该虚拟机的 uuid 字符串。该字符串在虚拟机对象创建时被初始化。
        """
        return self.__uuid;
    def updateInfo(self):
        """
        循环遍历各个信息对象，并调用它们的update()方法更新其信息
        """
        for k, v in self.__info.iteritems():
            v.update();
    def __getUsage(self):
        """
        组装使用信息字符串。私有方法。
        """
        result = { 'uuid': self.getUuid(), 'name': self.getName() };
        part = {};
        for k, v in self.__info.iteritems():
            part[k] = v.getUsage();
        result["size"] = part;
        # print "~~~~~~~~~", result, "~~~~~~~~~";
        return result;
    def getJsonUsage(self):
        return json.dumps(self.__getUsage());
    def __getNameByUuid(self, uuid):
        """
        根据UUID获取机器的NAME。私有方法。
        """
        #return "haha";
        param = { "action": "describe_instance", "instance_id": uuid };
        #print param;
        url = "http://%s:%s/%s?username=%s&password=%s&tenantId=%s&authenticate=true" % Properties.openStackConfigure;
        #print url;
        try:
            df = urllib.urlopen(url, json.dumps(param));
            response = df.read();
            response = json.loads(response);
            body = response["body"];
            name = body["name"];
            #print name;
            return name;
        except Exception as e:
            #print e;
            print str(e);
    def getName(self):
        """
        返回该虚拟机的 名字 字符串，以作为其它系统查找该虚拟机的依据。
        该字符串在虚拟机对象创建时被初始化。
        """
        return self.__name;

class HostMachine:
    def __init__(self):
        self.__conn = libvirt.openReadOnly("qemu:///system");
        self.__virtualMachines = {};   # 该主机上运行的虚拟机对象，采用键值对的方式存储，键是每个虚拟机的UUID，值是每个虚拟机对象。靠maintenanceVMs()方法周期性维护
        self.__list = [];              # 维护的是已经不存在的虚拟机（要删除的虚拟机）列表，每次虚拟机信息采集时就会对虚拟机是否需要删除进行判断
    def maintenanceVMs(self):
        """
        周期性维护虚拟机对象列表。运行的周期由配置文件中的 searchInterval 决定。
        """
        #print "--- 虚拟机列表维护 ---";
        # 列出当前主机中各个虚拟机的ID
        domIds = self.__conn.listDomainsID();
        # 针对每个虚拟机ID，进行操作：
        for domId in domIds:
            # 先根据虚拟机ID找到该虚拟机
            dom = self.__conn.lookupByID(domId);
            # 如果该虚拟机的UUID没有存在于当前主机的虚拟机列表中时
            if dom.UUIDString() not in self.__virtualMachines.keys():
                # 新建虚拟机对象，并将该虚拟机对象加入列表
                self.__virtualMachines[dom.UUIDString()] = VirtualMachine(dom);
                #print "向虚拟机列表中添加机器: ", dom.UUIDString();
                print "虚拟机 %s 上线" % dom.UUIDString();
    def updateVMsInfo(self):
        """
        更新运行于该主机上的所有虚拟机的状态信息，并且在更新信息的同时检查虚拟机的可用性。
        如果虚拟机不再可用，则从维护的虚拟机列表中删除该虚拟机对象。
        TODO：未来可能需要针对过程中发生的不同异常采取不同的处理策略。
        """
        #print "--- 虚拟机信息更新 ---";
        # 针对主机的虚拟机列表中的每台虚拟机：
        for m in self.__virtualMachines.itervalues():
            # 尝试：
            try:
                # 在本机中通过虚拟机的UUID信息找到该虚拟机
                validation = self.__conn.lookupByUUIDString(m.getUuid());
                # 并更新该虚拟机的信息
                m.updateInfo();
                #print "--------------------", m.getJsonUsage(), "---------------";
                # 在更新虚拟机的信息后，发送这些信息到服务器
                self.postInfoToServer(m.getJsonUsage());
            except Exception as e:
                print str(e);
                # 如果在上面尝试的过程中发生问题，则认为该虚拟机不可用，并将其加入*要删除的*虚拟机列表中
                self.__list.append(m.getUuid());
            else:
                pass
        # 如果*要删除的*虚拟机列表中有值
        for i in range(len(self.__list)):
            # 则依次将其从虚拟机列表中删除
            del self.__virtualMachines[self.__list[i]];
            #print "从虚拟机列表中删除机器: ", self.__list[i];
            print "虚拟机 %s 已下线" % self.__list[i];
        # 并清空*要删除的*虚拟机列表
        del self.__list[:];
    def postInfoToServer(self, jsonData):
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
        #print html;


if __name__ == "__main__":
    #ATs = AnalysisTimestamp(None);
    #ATs.update();
    #print ATs.getUsage();
    # 新建一个主机对象
    hostMachine = HostMachine();
    # 开始时第一次维护主机对象中的虚拟机列表
    hostMachine.maintenanceVMs();
    # 多少次抓取之后进行一次列表维护
    i = (Properties.searchInterval / Properties.fetchInterval) if (Properties.searchInterval / Properties.fetchInterval > 0) else 1;
    # 计数项。当达到需要维护列表的次数时，维护列表，并将其重置为 0
    j = 0;
    while True:
        j += 1;
        hostMachine.updateVMsInfo();
        time.sleep(Properties.fetchInterval);
        if i == j:
            j = 0;
            hostMachine.maintenanceVMs();
            