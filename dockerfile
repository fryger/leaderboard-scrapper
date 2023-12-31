FROM public.ecr.aws/lambda/python:3.9

# Install chrome dependecies
RUN yum install unzip atk at-spi2-atk gtk3 cups-libs pango libdrm \ 
    libXcomposite libXcursor libXdamage libXext libXtst libXt \
    libXrandr libXScrnSaver alsa-lib -y

# Copy install scripts
COPY requirements.txt /tmp/
COPY install-chrome.sh /tmp/

# Install chromium, chrome-driver
RUN /usr/bin/bash /tmp/install-chrome.sh

# Install Python dependencies for function
RUN pip install --upgrade pip -q
RUN pip install -r /tmp/requirements.txt -q

# Remove unused packages
RUN yum remove unzip -y

COPY lambda_function.py /var/task/
CMD [ "lambda_function.lambda_handler" ] 