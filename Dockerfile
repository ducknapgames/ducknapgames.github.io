FROM nginx:stable-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -rf /usr/share/nginx/html/*
COPY index.html index.md privacy.html robots.txt sitemap.xml llms.txt games.json app-ads.txt /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
COPY games/ /usr/share/nginx/html/games/
COPY privacy/ /usr/share/nginx/html/privacy/
COPY support/ /usr/share/nginx/html/support/
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1/robots.txt || exit 1
