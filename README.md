# ulab-access-proxy
Access Proxy for ulab devices and services.

Use nginx as a TCP/UDP/HTTP(S) forward/reverse proxy server.

Nginx [engine x] is a high-performance HTTP and reverse proxy server, a mail proxy server, and a universal TCP/UDP proxy server.

## Nginx

How to build portable nginx image for ulab devices and services.

### Build

```bash
cd nginx
./compile <version>
```

### Run

```bash
# cd nginx
# ./nginx -h
nginx version: nginx/1.26.1
Usage: nginx [-?hvVtTq] [-s signal] [-p prefix]
             [-e filename] [-c filename] [-g directives]

Options:
  -?,-h         : this help
  -v            : show version and exit
  -V            : show version and configure options then exit
  -t            : test configuration and exit
  -T            : test configuration, dump it and exit
  -q            : suppress non-error messages during configuration testing
  -s signal     : send signal to a master process: stop, quit, reopen, reload
  -p prefix     : set prefix path (default: ./)
  -e filename   : set error log file (default: logs/error.log)
  -c filename   : set configuration file (default: conf/nginx.conf)
  -g directives : set global directives out of configuration file
# nginx -p /path/to/nginx/dir
```