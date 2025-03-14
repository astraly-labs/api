# Pragma Interactive API

![image](https://github.com/Astraly-Labs/Pragma/assets/12902455/45243fd4-5a1d-4b85-864f-2ceca50c7f79)

Interactive API for Pragma Node

### Setup

```bash
cp .env.example .env
```

and then set the `PRAGMA_API_KEY` and `PRAGMA_API_BASE_URL` variables.

## Running the API

```bash
docker compose up --build
```

## Running the API with Uvicorn

```bash
uvicorn pragma.main:app --host 0.0.0.0 --port 8007
```
