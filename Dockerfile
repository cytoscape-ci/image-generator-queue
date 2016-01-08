FROM python:3.5.1

MAINTAINER Keiichiro Ono <kono@ucsd.edu>

# Install Python dependencie
RUN pip install requests luigi flask flask-restful

# Add directory for REST API server code
RUN mkdir /app
WORKDIR /app
ADD . /app

EXPOSE 3001 8082

# Run API server
CMD ["./run.sh"]