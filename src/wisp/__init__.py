def main() -> None:
    import uvicorn

    uvicorn.run("wisp.api:app", host="127.0.0.1", port=8899)
