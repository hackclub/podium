FROM python:3.13-slim

RUN pip install poetry


RUN mkdir /app
WORKDIR /app

COPY . /app

RUN ["poetry", "install"]

RUN ["poetry", "run", "--", "playwright","install"]
CMD ["poetry", "run", "--", "python", "-m", "uvicorn", "podium.main:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["poetry", "run", "python", "-m", "uvicorn", "podium.main:app", "--host", "0.0.0.0", "--port", "8000"]