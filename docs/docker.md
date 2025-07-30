
# mysql启动命令

```bash
docker run \
--name mysql \
-d \
-p 3306:3306 \
--restart always \
-v /mydata/mysql/log:/var/log/mysql \
-v /mydata/mysql/data:/var/lib/mysql \
-v /mydata/mysql/conf:/etc/mysql/conf.d \
-e MYSQL_ROOT_PASSWORD=zhangzc123.. \
-e MYSQL_DATABASE=sub \
-e MYSQL_USER=zhangzc \
-e MYSQL_PASSWORD=zhangzc123.. \
mysql:latest \
--character-set-server=utf8mb4 \
--collation-server=utf8mb4_unicode_ci \
--default-time-zone=+8:00
```


# 启动 we-mp-rss

```bash
docker run -d \
  --name we-mp-rss \
  -p 8001:8001 \
  -e DB=mysql+pymysql://zhangzc:zhangzc123..@119.8.32.27:3306/sub?charset=utf8mb4 \
  -e USERNAME=zhangzc \
  -e PASSWORD=zhangzc123.. \
  -e DINGDING_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=5f7559a8270318675d08778a784817df10178c6b0b217c45f35d0db430bd96ff \
  -v /we-mp-rss/data:/app/data \
  ghcr.io/rachelos/we-mp-rss:latest
```