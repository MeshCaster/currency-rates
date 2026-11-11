import uvicorn


def main() -> None:
    uvicorn.run("host.app:create_app", factory=True, host="0.0.0.0", port=8000,
                log_config=None, access_log=False)


if __name__ == "__main__":
    main()
