# Messages

Full inbox/outbox management with threading, attachments, and label support.

## Reading Messages

```python
from smartschool import Smartschool, PathCredentials, MessageHeaders, Message, BoxType

session = Smartschool(PathCredentials())

# List inbox messages (default)
for header in MessageHeaders(session):
    print(f"{'[NEW] ' if header.unread else ''}From: {header.from_} - {header.subject} ({header.date})")

# List sent messages
for header in MessageHeaders(session, box_type=BoxType.SENT):
    print(f"{header.subject}")
```

Available box types: `INBOX`, `DRAFT`, `SCHEDULED`, `SENT`, `TRASH`.

### Sorting

```python
from smartschool import SortField, SortOrder

# Sort by sender, ascending
headers = MessageHeaders(session, sort_by=SortField.FROM, sort_order=SortOrder.ASC)
```

Available sort fields: `DATE`, `FROM`, `READ_UNREAD`, `ATTACHMENT`, `FLAG`.

### Full Message Content

```python
header = list(MessageHeaders(session))[0]

for msg in Message(session, header.id):
    print(f"From: {msg.from_}")
    print(f"Subject: {msg.subject}")
    print(f"Body: {msg.body}")
    print(f"Receivers: {msg.receivers}")
```

## Attachments

```python
from smartschool import Attachments
from pathlib import Path

for header in MessageHeaders(session):
    if header.attachment:
        for attachment in Attachments(session, header.id):
            content = attachment.download()
            Path(f"attachments/{attachment.name}").write_bytes(content)
            print(f"Downloaded: {attachment.name} ({attachment.size})")
```

## Composing and Sending Messages

```python
from smartschool import Smartschool, PathCredentials, MessageComposerForm, RecipientType
from pathlib import Path

session = Smartschool(PathCredentials())

# Create a new message compose form
form = MessageComposerForm.create(session=session)

# Set subject and message content
form.set_subject("Hello")
form.set_message_html("<p>This is my message</p>")

# Search for recipients
users, groups = form.search_users("John")

# Add recipients
if users:
    form.add_recipient(users[0], RecipientType.TO)

if groups:
    form.add_recipient(groups[0], RecipientType.CC)

# Add attachments
form.add_attachment("path/to/document.pdf")
form.add_attachment("path/to/image.png")

# Send the message
response = form.send()
print(f"Message sent: {response.status_code}")
```

### Recipient Types

```python
from smartschool import RecipientType

# Available recipient types
RecipientType.TO    # To field
RecipientType.CC    # Carbon copy
RecipientType.BCC   # Blind carbon copy
```

### Searching Recipients

```python
# Search for recipients (users and groups)
users, groups = form.search_users("search term")

# Users have properties: userID, value (display name), ssID, coaccountname, classname, schoolname, picture
for user in users:
    print(f"User: {user.value}")

# Groups have properties: groupID, value, icon, ssID, description
for group in groups:
    print(f"Group: {group.value}")
```

### Direct Field Setting

For advanced use cases, set custom payload fields directly:

```python
# Set arbitrary form fields
form.set_field("copyToLVS", "copyToLVS")  # Copy to learning management system
form.set_field("sendDate", "2024-04-10")  # Schedule sending

# Send the message
response = form.send()
```

## Message Operations

### Mark as Unread

```python
from smartschool import MarkMessageUnread

result = list(MarkMessageUnread(session, msg_id=12345))[0]
```

### Apply Labels

```python
from smartschool import AdjustMessageLabel, MessageLabel

list(AdjustMessageLabel(session, msg_id=12345, label=MessageLabel.RED_FLAG))
```

Available labels: `NO_FLAG`, `GREEN_FLAG`, `YELLOW_FLAG`, `RED_FLAG`, `BLUE_FLAG`.

### Archive and Delete

```python
from smartschool import MessageMoveToArchive, MessageMoveToTrash

# Archive one or multiple messages
MessageMoveToArchive(session, msg_id=12345).get()
MessageMoveToArchive(session, msg_id=[12345, 67890]).get()

# Move to trash
list(MessageMoveToTrash(session, msg_id=12345))
```

## Polling for New Messages

Use `already_seen_message_ids` to only get new messages:

```python
seen_ids = []

for header in MessageHeaders(session, already_seen_message_ids=seen_ids):
    print(f"New: {header.subject}")
    seen_ids.append(header.id)
```
