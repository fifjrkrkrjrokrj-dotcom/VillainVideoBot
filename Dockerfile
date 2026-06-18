FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data logs templates

EXPOSE 8501

CMD ["sh", "-c", "python bot.py & streamlit run admin_panel.py --server.port=8501 --server.address=0.0.0.0"]
