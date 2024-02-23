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


# Testing on the provided URL
url = 'https://www.bramadams.dev/my-thoughts-on-solo-leveling/'
plaintext = extract_plaintext(url)
print(plaintext)