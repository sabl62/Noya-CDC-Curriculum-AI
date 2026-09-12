import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.views import get_ai_service

service = get_ai_service()

try:
    print(service.generate_title("what is gravity?"))
    print("Title generation works")
except Exception as e:
    print("Error in title generation:")
    print(e)

try:
    gen = service.chat("what is gravity?")
    # exhaust first few events to validate generator works
    first_events = []
    for i, event in enumerate(gen):
        first_events.append(event)
        if i >= 3:
            break
    print("First chat events:", first_events)
    print("Chat generator works")
except Exception as e:
    print("Error in chat:")
    print(e)
