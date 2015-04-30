#!/usr/bin/python
# -*- coding: UTF-8 -*-

import json;
import time;
import sqlite3;

from wsgiref.simple_server import make_server;

"""
作用：虚拟机运行情况检测服务器端
作者：王子超
邮箱：evilic@qq.com


目前想到的可以改善的地方有：
1 自动添加iptables规则
2 检查Ctrl-c的键入，并返回给客户端代码，以停止客户端数据的更新操作
3 为优化性能，可以减少客户端与服务器通信的次数
"""

# 端口号设置
# 设置后请注意给 iptables 添加规则：
# iptables -I INPUT -p tcp --dport 端口号 -j ACCEPT
# service iptables save
port = 18040;

# sqlite3 数据库目录设置（包含数据库文件名）
dbLocate = "fdb";
# 数据库表结构说明：略

class Database:
    def __init__(self):
        # 打开数据库连接
        #print dbLocate;
        self.__conn = sqlite3.connect(dbLocate);
        # 获取游标
        self.__cursor = self.__conn.cursor();
    def getHostsList(self):
        """
        获得数据库中现有的主机记录
        """
        self.__cursor.execute("SELECT DISTINCT `uuid` FROM `vps_monitor`");
        res = self.__cursor.fetchall();
        #print res;
        result = [];
        for rec in res:
            #print len(rec);
            result.append(rec[0].encode("utf-8"));
        #print result;
        return result;
    def save(self, uuid, jsonData, name):
        """
        对于不存在于数据库中的主机记录，采取添加的策略
        """
        ts = time.time(); # 此变量的存在源于早期版本的实现设计，现在的存在合理性待讨论
        self.__cursor.execute("INSERT INTO `vps_monitor` VALUES (NULL, ?, ?, ?, ?)", [uuid, jsonData, name, ts]);
        self.__conn.commit();
        return ts;
    def delete(self, uuid):
        """
        此方法不被使用
        """
        self.__cursor.execute("DELETE FROM `vps_monitor` WHERE `uuid` = ?", [uuid]);
        self.__conn.commit();
    def update(self, uuid, jsonData, name):
        """
        对于已存在于数据库中的主机记录，采取更新的策略
        """
        ts = time.time(); # 此变量的存在源于早期版本的实现设计，现在的存在合理性待讨论
        self.__cursor.execute("UPDATE `vps_monitor` SET `size` = ?, `name` = ?, `time` = ? WHERE `uuid` = ?", [jsonData, name, ts, uuid]);
        self.__conn.commit();
        return ts;
    def close(self):
        """
        关闭数据库连接
        """
        self.__cursor.close();
        self.__conn.close();

def application(environ, start_response):
    """
    post来的application/json数据格式：
    {
    "uuid" : "adsqq-adfax-dqeba",
    "size" : "{ \"cpu\" : [0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00], \"time\" : [123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456] }",
    "name" : "hahahaha"
    }
    """
    # 获得客户端发来数据的长度
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0));
    except (ValueError):
        request_body_size = 0;
    # 根据数据的长度，获取到客户端发来的数据内容
    request_body = environ['wsgi.input'].read(request_body_size);
    #print "---request_body: ", request_body;
    # 解析数据内容
    data = json.loads(request_body);
    #print "---uuid: ", data["uuid"];
    #print hostsList;
    #print data["uuid"] in hostsList;
    #print "---size: ", json.dumps(data["size"]);
    #print "---name: ", data["name"];
    # 判断该虚拟机是否已经存在于数据库中
    # 目前采用的是在控制端进行判断，未来可以修改为 Database 类自己维护
    if data["uuid"] not in hostsList:
        # 如果不存在于数据库中，则进行数据库的插入操作
        success = db.save(data["uuid"], json.dumps(data["size"]), data["name"]);
        # 将该 uuid 添加进入 hostsList 中
        hostsList.append(data["uuid"]);
        print "添加新的虚拟机信息: ", data["uuid"];
    else:
        # 否则进行数据库的更新操作
        success = db.update(data["uuid"], json.dumps(data["size"]), data["name"]);
        print data["uuid"], "信息被更新。";
    # 设置返回的状态码
    status = "200 OK"; # HTTP Status
    headers = [("Content-type", "text/html")]; # HTTP Headers
    start_response(status, headers);
    # The returned object is going to be printed
    # 返回数据给客户端
    return "%.3f" % (success);

# 新建数据库连接
db = Database();
# 检查已经存在于数据库中的虚拟机记录
hostsList = db.getHostsList();
# 开始接受 post 请求
httpd = make_server('', port, application);
print "服务端已运行于 %s 端口……" % port;

# Serve until process is killed
httpd.serve_forever();
