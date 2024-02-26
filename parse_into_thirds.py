import requests
from bs4 import BeautifulSoup

def extract_plaintext(url):
    if"bramadams.dev" not in url:
        return "Not a bramadams.dev URL"
    response = requests.get(url)
    # i only need the text from c-post__content
    soup = BeautifulSoup(response.text, 'html.parser')
    c_post_content = soup.find_all('div', class_='c-post__content')
    if len(c_post_content) == 0:
        return "No c-post__content found"
    soup = c_post_content[0]
    # Custom function to process HTML
    def process_html(tag):
        text = ''
        for child in tag.children:
            if child.name in ['p', 'li']:
                text += '\n' + process_html(child) + '\n'
            elif child.name is None:  # NavigableString
                text += child.string
            else:
                text += process_html(child)
        return text

    return process_html(soup).strip()

def split_into_sublists(text, max_len):
    assert max_len > 0
    assert len(text) > 0

    lines = text.split('\n')  # Split the text into lines
    sublists = []  # List of sublists
    current_list = []  # Current sublist
    current_length = 0  # Length of the current sublist

    for line in lines:
        line_length = len(line)
        if current_length + line_length + len(current_list) > max_len:  # If adding the line would exceed the max length
            sublists.append('\n'.join(current_list))  # Add the current sublist to the list of sublists
            current_list = [line]  # Start a new sublist
            current_length = line_length  # Set the length of the new sublist
        else:
            current_list.append(line)
            current_length += line_length

    if current_list:
        sublists.append('\n'.join(current_list))

    return sublists

def parse_into_thirds(plaintext):
    thirds = split_into_sublists(plaintext, len(plaintext) // 3)
    if len(thirds) > 3:
        # Merge the last two sections if there are more than three sections
        thirds[-2] += '\n---\n' + thirds[-1]
        thirds.pop(-1)
    return thirds



# Testing on the provided URL
url = 'https://www.bramadams.dev/my-thoughts-on-nefertiti/'
plaintext = extract_plaintext(url)
# print(plaintext)
print(len(plaintext) // 3)
thirds = parse_into_thirds(plaintext)
i = 0
titles = ["First Section", "Second Section", "Third Section"]
for third in thirds:
    print("## " + titles[i])
    print(third)
    i += 1
    