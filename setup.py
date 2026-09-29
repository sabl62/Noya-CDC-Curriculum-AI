import platform as p
import subprocess as sp

ENV_PATH = "backend-main/.env.test"


def detect():
    return p.system()


if detect() in ("Windows", "Darwin", "Linux"):
    def acq_gemini():
        print("For Gemini API Key: https://aistudio.google.com/apikey")

        with open(ENV_PATH, "w") as env:
            i = 1

            while i <= 4:
                apik = input(f"Enter gemini API Key {i}: ")

                if i == 1 and apik == "":
                    print("1st API Key is mandatory, you can skip others")
                    continue

                env.write(f"GEMINI_API_KEY_{i}={apik}\n")
                i += 1

    def acq_dpsk():
        print("For deepseek API Key: https://platform.deepseek.com")

        with open(ENV_PATH, "a") as env:
            env.write("DEEPSEEK_ENDPOINT=https://api.deepseek.com/v1\n")

            i = 1

            while i <= 4:
                apik = input(f"Enter deepseek API Key {i}: ")

                if i == 1 and apik == "":
                    print("1st API Key is mandatory, you can skip others")
                    continue

                env.write(f"DEEPSEEK_API_KEY_{i}={apik}\n")
                i += 1

    def acq_spb():
        print("For Database URI : visit Supabase, Neon or any other PostgreSQL service")
        print("You can Skip it if you want to use default django SQLite")

        while True:
            sk_prompt = input("Skip this Step? (y/n): ").strip()

            if sk_prompt.lower() == "n":
                while uri == "":
                    uri = input("Enter the psql database URI: ")

                with open(ENV_PATH, "a") as env:
                    env.write(f"DATABASE_URL={uri}\n")

                break

            elif sk_prompt.lower() == "y":
                print("continuing with next step...")
                break

            else:
                print("Enter a valid response.")

    def acq_qdr():
        print("For Qdrant API Key and URL, : https://cloud.qdrant.io")

        apik = input("Enter QDrant API Key: ")

        while apik == "":
            print("REQUIRED!! You cant skip this.")
            apik = input("Enter QDrant API Key: ")

        url = input("Enter QDrant URL: ")

        while url == "":
            print("REQUIRED!! You cant skip this.")
            url = input("Enter QDrant URL: ")

        with open(ENV_PATH, "a") as env:
            env.write(f"QDRANT_API_KEY={apik}\n")
            env.write(f"QDRANT_URL={url}\n")

    acq_gemini()
    acq_dpsk()
    acq_spb()
    acq_qdr()

    print("Enviroment Setup Complete!")
    print("Moving on, to RAG Initialization and Server Srating!")

    def bsetup():
        print("Setting Up Backend Now!")

        backend_dir = "backend-main"

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

        sp.run(
            [pip, "install", "-r", "backend-main/requirements.txt"],
            check=True
        )

        sp.run(
            [python, "manage.py", "migrate"],
            cwd=backend_dir,
            check=True
        )

        sp.run(
            [python, "manage.py", "initialize_rag"],
            cwd=backend_dir,
            check=True
        )

        sp.run(
            [python, "manage.py", "runserver"],
            cwd=backend_dir,
            check=True
        )

    def fsetup():
        print("Setting Up Frontend Now!")

        sp.Popen([
            "powershell",
            "-NoExit",
            "-Command",
            "cd frontend; npm install; npm run dev"
        ])

else:
    print("Unsupported OS!")
