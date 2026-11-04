FROM nginx:stable-alpine
RUN apk add --no-cache python3
COPY deploy/statistics/nginx-statistics.conf /etc/nginx/conf.d/00-statistics.conf
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/statistics/server.py /opt/ducknap-statistics/server.py
COPY deploy/statistics/40-statistics.sh /docker-entrypoint.d/40-statistics.sh
RUN chmod 755 /docker-entrypoint.d/40-statistics.sh
RUN rm -rf /usr/share/nginx/html/*
COPY index.html index.md privacy.html robots.txt sitemap.xml llms.txt games.json app-ads.txt /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
COPY games/ /usr/share/nginx/html/games/
COPY privacy/ /usr/share/nginx/html/privacy/
COPY support/ /usr/share/nginx/html/support/
# Keep locale directories separate so every translated route remains addressable.
COPY ja/ /usr/share/nginx/html/ja/
COPY ko/ /usr/share/nginx/html/ko/
COPY de/ /usr/share/nginx/html/de/
COPY zh-Hant/ /usr/share/nginx/html/zh-Hant/
COPY fr/ /usr/share/nginx/html/fr/
COPY es/ /usr/share/nginx/html/es/
COPY pt-BR/ /usr/share/nginx/html/pt-BR/
COPY it/ /usr/share/nginx/html/it/
COPY ar/ /usr/share/nginx/html/ar/
COPY th/ /usr/share/nginx/html/th/
COPY tr/ /usr/share/nginx/html/tr/
COPY id/ /usr/share/nginx/html/id/
COPY pl/ /usr/share/nginx/html/pl/
COPY nl/ /usr/share/nginx/html/nl/
COPY vi/ /usr/share/nginx/html/vi/
# The collector accepts only existing published document routes, never arbitrary URLs.
RUN python3 -c "import json,pathlib; r=pathlib.Path('/usr/share/nginx/html'); pathlib.Path('/opt/ducknap-statistics/routes.json').write_text(json.dumps(sorted('/'+str(p.relative_to(r)).removesuffix('index.html') for p in r.rglob('index.html'))))"
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1/robots.txt || exit 1
