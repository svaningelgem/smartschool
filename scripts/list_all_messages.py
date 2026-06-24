from smartschool import MessageHeaders, PathCredentials, Smartschool

session = Smartschool(PathCredentials())

# List inbox messages (default)
for header in MessageHeaders(session):
    print(f"{'[NEW] ' if header.unread else ''}From: {header.from_} - {header.subject} ({header.date})")
