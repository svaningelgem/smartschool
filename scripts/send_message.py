from smartschool import MessageComposerForm, PathCredentials, RecipientType, Smartschool

session = Smartschool(PathCredentials())

form = MessageComposerForm.create(session=session)
form.set_subject("test 3")
form.set_message_html("<p>mijn test bericht</p>")

users, groups = form.search_users("username")

print("Users:")
for user in users:
    print(f"- {user.value} (ID: {user.user_id})")

print("\nGroups:")
for group in groups:
    print(f"- {group.value} (ID: {group.group_id})")

if users:
    form.add_recipient(users[0], RecipientType.TO)
    form.add_attachment("README.md")


resp = form.send()
print(resp.status_code)
