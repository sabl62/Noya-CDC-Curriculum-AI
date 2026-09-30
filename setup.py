import platform as p
import subprocess as sp

ENV_PATH = "backend-main/.env.test"

RESET = "\033[0m"
PINE = "\033[38;5;30m"
MINT = "\033[38;5;79m"
BRASS = "\033[38;5;179m"
CORAL = "\033[38;5;173m"
MUTED = "\033[38;5;245m"
WHITE = "\033[38;5;255m"


def styled(text, color):
    return f"{color}{text}{RESET}"


def divider():
    print(styled("  " + "─" * 58, PINE))


def title(name, detail):
    print()
    divider()
    print(styled(f"  {name}", WHITE))
    print(styled(f"  {detail}", MUTED))
    divider()


def prompt(message):
    return input(f"  {styled('›', MINT)} {message}")


def note(message):
    print(f"  {styled('[i]', BRASS)} {message}")


def success(message):
    print(f"  {styled('[+]', MINT)} {message}")


def warning(message):
    print(f"  {styled('[!]', CORAL)} {message}")


def detect():
    return p.system()


if detect() in ("Windows", "Darwin", "Linux"):
    def acq_gemini():
        title("01  CONNECT YOUR AI", "Gemini is required. Add up to four keys for reliability.")
        print(f"  Gemini API key: {styled('https://aistudio.google.com/apikey', MINT)}")

        with open(ENV_PATH, "w") as env:
            i = 1

            while i <= 4:
                apik = prompt(f"Enter Gemini API key {i}: ")

                if i == 1 and apik == "":
                    warning("The first Gemini API key is required. You can skip the remaining keys.")
                    continue

                env.write(f"GEMINI_API_KEY_{i}={apik}\n")
                i += 1

        success("Gemini settings saved.")

    def acq_dpsk():
        title("02  ADD A SECOND AI PROVIDER", "DeepSeek is required. Additional keys are optional.")
        print(f"  DeepSeek API key: {styled('https://platform.deepseek.com', MINT)}")

        with open(ENV_PATH, "a") as env:
            env.write("DEEPSEEK_ENDPOINT=https://api.deepseek.com/v1\n")

            i = 1

            while i <= 4:
                apik = prompt(f"Enter DeepSeek API key {i}: ")

                if i == 1 and apik == "":
                    warning("The first DeepSeek API key is required. You can skip the remaining keys.")
                    continue

                env.write(f"DEEPSEEK_API_KEY_{i}={apik}\n")
                i += 1

        success("DeepSeek settings saved.")

    def acq_spb():
        title("03  DATABASE", "Connect PostgreSQL or keep the default Django SQLite database.")
        note("For a PostgreSQL URI, visit Supabase, Neon, or another PostgreSQL service.")

        while True:
            sk_prompt = prompt("Skip PostgreSQL setup and use SQLite? (y/n): ").strip()

            if sk_prompt.lower() == "n":
                uri = ""
                while uri == "":
                    uri = prompt("Enter the PostgreSQL database URI: ").strip()
                    if uri == "":
                        warning("A database URI is required to continue.")

                with open(ENV_PATH, "a") as env:
                    env.write(f"DATABASE_URL={uri}\n")

                success("PostgreSQL connection saved.")
                break

            elif sk_prompt.lower() == "y":
                note("Continuing with the default SQLite database.")
                break

            else:
                warning("Enter y to use SQLite or n to configure PostgreSQL.")

    def acq_qdr():
        title("04  CURRICULUM SEARCH", "Connect Qdrant to enable curriculum search and retrieval.")
        print(f"  Qdrant dashboard: {styled('https://cloud.qdrant.io', MINT)}")

        apik = prompt("Enter Qdrant API key: ")

        while apik == "":
            warning("A Qdrant API key is required.")
            apik = prompt("Enter Qdrant API key: ")

        url = prompt("Enter Qdrant URL: ")

        while url == "":
            warning("A Qdrant URL is required.")
            url = prompt("Enter Qdrant URL: ")

        with open(ENV_PATH, "a") as env:
            env.write(f"QDRANT_API_KEY={apik}\n")
            env.write(f"QDRANT_URL={url}\n")

        success("Qdrant settings saved.")

    print()
    print(styled("  N O Y A", MINT))
    print(styled("  CDC CURRICULUM AI  /  SETUP", WHITE))
    print(styled("  Let’s get your learning workspace ready.", MUTED))
    print(styled("  " + "═" * 58, PINE))

    acq_gemini()
    acq_dpsk()
    acq_spb()
    acq_qdr()

    print()
    success("Environment setup complete.")
    note("Moving on to curriculum search initialization and server startup.")

    def bsetup():
        title("05  BACKEND", "Preparing the server environment and curriculum index.")

        backend_dir = "backend-main"

        note("Creating the Python virtual environment.")
        sp.run(
            ["python", "-m", "venv", "venv"],
            cwd=backend_dir,
            check=True
        )

        if detect() == "Windows":
            python = "backend-main/venv/Scripts/python.exe"
            pip = "backend-main/venv/Scripts/pip.exe"
        else:
            python = "backend-main/venv/bin/python"
            pip = "backend-main/venv/bin/pip"

        note("Installing backend packages.")
        sp.run(
            [pip, "install", "-r", "backend-main/requirements.txt"],
            check=True
        )

        note("Preparing the database.")
        sp.run(
            [python, "manage.py", "migrate"],
            cwd=backend_dir,
            check=True
        )

        note("Initializing curriculum search.")
        sp.run(
            [python, "manage.py", "initialize_rag"],
            cwd=backend_dir,
            check=True
        )

        success("Backend setup complete.")
        note("Starting the Noya server.")
        sp.run(
            [python, "manage.py", "runserver"],
            cwd=backend_dir,
            check=True
        )

    def fsetup():
        title("06  FRONTEND", "Preparing the Noya web app in a separate terminal.")

        sp.Popen([
            "powershell",
            "-NoExit",
            "-Command",
            "cd frontend; npm install; npm run dev"
        ])

    bsetup()
    fsetup()

else:
    warning("Unsupported operating system.")
