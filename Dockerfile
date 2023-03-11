FROM python:3.9-slim

WORKDIR /flask_app

COPY flask_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./flask_app .

EXPOSE 5000

CMD ["python", "app.py"]
