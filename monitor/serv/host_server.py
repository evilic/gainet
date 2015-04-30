#!/usr/bin/python
# -*- coding: UTF-8 -*-

import json;
import time;
import sqlite3;

from wsgiref.simple_server import make_server;

"""
作用：主机运行情况记录服务器端
作者：王子超
邮箱：evilic@qq.com
"""

# 端口号设置
# 设置后请注意给 iptables 添加规则：
# iptables -I INPUT -p tcp --dport 端口号 -j ACCEPT
# service iptables save
port = 18041;

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
        self.__cursor.execute("SELECT DISTINCT `name` FROM `host_monitor`");
        res = self.__cursor.fetchall();
        #print res;
        result = [];
        for rec in res:
            #print len(rec);
            result.append(rec[0].encode("utf-8"));
        #print result;
        return result;
    def save(self, name, memJs, cpuJs, netJs, ioJs):
        """
        对于不存在于数据库中的主机记录，采取添加的策略
        """
        self.__cursor.execute("INSERT INTO `host_monitor` VALUES (NULL, ?, ?, ?, ?, ?)", [name, memJs, cpuJs, netJs, ioJs]);
        self.__conn.commit();
        return "OK";
    def update(self, memJs, cpuJs, netJs, ioJs, name):
        """
        对于已存在于数据库中的主机记录，采取更新的策略
        """
        self.__cursor.execute("UPDATE `host_monitor` SET `mem` = ?, `cpu` = ?, `net` = ?, `io` = ? WHERE `name` = ?", [memJs, cpuJs, netJs, ioJs, name]);
        self.__conn.commit();
        return "OK";
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
    "name" : "host101",
    "mem" : "{ \"data\" : [0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00], \"time\" : [123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456] }",
    "cpu" : "{ \"data\" : [0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00], \"time\" : [123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456] }",
    "net" : "{ \"data\" : [0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00], \"time\" : [123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456] }",
    "io" : "{ \"data\" : [0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00, 10.2, 15.2, 0.00], \"time\" : [123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456, 123456789.012456] }"
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
    #print "---name: ", data["name"];
    #print hostsList;
    #print data["name"] in hostsList;
    #print "---mem: ", json.dumps(data["mem"]);
    # 判断该主机是否已经存在于数据库中
    # 目前采用的是在控制端进行判断，未来可以修改为 Database 类自己维护
    if data["name"] not in hostsList:
        # 如果不存在于数据库中，则进行数据库的插入操作
        success = db.save(data["name"], json.dumps(data["mem"]), json.dumps(data["cpu"]), json.dumps(data["net"]), json.dumps(data["io"]));
        # 将该 name 添加进入 hostsList 中
        hostsList.append(data["name"]);
        print "添加新的HOST主机信息: ", data["name"];
    else:
        # 否则进行数据库的更新操作
        success = db.update(json.dumps(data["mem"]), json.dumps(data["cpu"]), json.dumps(data["net"]), json.dumps(data["io"]), data["name"]);
        print data["name"], "信息被更新。";
    # 设置返回的状态码
    status = "200 OK"; # HTTP Status
    headers = [("Content-type", "text/html")]; # HTTP Headers
    start_response(status, headers);
    # The returned object is going to be printed
    # 返回数据给客户端
    return success;

# 新建数据库连接
db = Database();
# 检查已经存在于数据库中的虚拟机记录
hostsList = db.getHostsList();
# 开始接受 post 请求
httpd = make_server('', port, application);
print "服务端已运行于 %s 端口……" % port;

# Serve until process is killed
httpd.serve_forever();
