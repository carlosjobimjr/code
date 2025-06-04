FROM nginx

COPY nginx.conf /etc/nginx/conf.d
COPY proxy_params /etc/nginx
RUN true
COPY nginx-selfsigned.crt /etc/ssl/certs/
RUN true
COPY nginx-selfsigned.key /etc/ssl/private/
RUN true
COPY ssl-params.conf /etc/nginx/snippets/
RUN true
COPY self-signed.conf /etc/nginx/snippets/
RUN true
COPY dhparam.pem /etc/nginx/
