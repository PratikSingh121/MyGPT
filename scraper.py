import os
import requests
from bs4 import BeautifulSoup
import concurrent.futures
from urllib.parse import urlparse, urlsplit
import argparse 

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'

def get_page_content(url):
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT})
        response.raise_for_status()  
        return response.content

    except requests.exceptions.RequestException as e:
        # print(f"Error while fetching the page: {e}")
        return None

def get_base_domain(url):
    # Use urlsplit to break down the URL into components
    url_components = urlsplit(url)

    # Extract the netloc, which contains the domain and possibly the subdomain
    netloc = url_components.netloc

    # Split the netloc into subdomain and domain
    subdomain, _, domain = netloc.partition('.')

    # Combine the subdomain and domain to get the base domain
    base_domain = f"{subdomain}.{domain}"

    return base_domain

def get_links_from_page(soup, base_url):
    base_domain = get_base_domain(base_url)
    base_url = f"https://{base_domain}/"
    try:
        links = []
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            if link.startswith('http'):
                if base_domain not in link:
                    continue
                links.append(link)
            elif link.startswith('/'):
                links.append(base_url + link[1:])
            elif link.startswith('#'):
                pass
            else:
                links.append(base_url + link)
        return links

    except Exception as e:
        print(f"Error while extracting links: {e}")
        return []


def scrape_website_and_links(url, selector, max_depth=2,visited=None):
    page_data = ""

    if visited is None:
        visited = set()

    if max_depth == 0 or url in visited:
        return []

    print(f"Scraping: {url}")
    visited.add(url)

    page_content = get_page_content(url)

    if page_content is None:
        return []

    soup = BeautifulSoup(page_content, 'html5lib')

    try:
        title = soup.title.text
    except AttributeError:
        title = ''
    selected_elements = soup.select('.max-w-none')

    for element in selected_elements:
        page_data += element.text
    page_data = page_data.replace('\n\n', '\n')
    # numbers = scrape_phone_numbers(soup)
    # emails = scrape_emails(soup)
    # social_media_links = scrape_social_media_links(soup)
    if page_data != "":
        output = [{'title': title, 'url': url, 'data': page_data}]
    else:
        output = []

    links = get_links_from_page(soup, url)

    with concurrent.futures.ThreadPoolExecutor() as executor:

        future_to_link = {executor.submit(scrape_website_and_links, link, selector, max_depth - 1, visited): link for link in links}
        for future in concurrent.futures.as_completed(future_to_link):
            sub_output = future.result()
            output.extend(sub_output)

    return output

def read_url_from_file(file_path):
    try:
        with open(file_path, 'r') as file:

            domains = [line.strip() for line in file.readlines()]
            return domains
    except Exception as e:
        print(f"Error while reading file: {e}")
        return []

if __name__ == "__main__":
    final_results = []

    parser = argparse.ArgumentParser(description="Website Scraper")

    parser.add_argument("-u", "--url", type=str, help="URL to start scraping")
    parser.add_argument("-d", "--depth", type=int, help="Maximum depth to crawl (an integer) [Default:2]")
    parser.add_argument("-f", "--file", type=str, help="Path to a file with domains")
    parser.add_argument("-s", "--selector", type=str, help="CSS selector to use for scraping")

    args = parser.parse_args()

    if args.url and args.file:
        print("Error: Both -l and -f options cannot be used together.")
        parser.print_help()
        exit()

    if args.file:
        domains = read_url_from_file(args.file)
        if not domains:
            print("No URL found in the file.")
            exit()

        selector = args.selector if args.selector else "p"
        max_depth_to_crawl = args.depth if args.depth else 2

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_domain = {executor.submit(scrape_website_and_links, domain, selector, max_depth_to_crawl): domain for domain in domains}
            for future in concurrent.futures.as_completed(future_to_domain):
                domain = future_to_domain[future]
                output = future.result()
                site_count = len(output)

                parsed_url = urlparse(domain)
                domain_name = parsed_url.netloc

                output_path = os.path.join(os.getcwd(),"storage", domain_name)
                os.makedirs(output_path, exist_ok=True)
                print(f"Output for {domain} will be saved in the folder: {output_path}")
                output_file_location = os.path.join(output_path, "output.json")

                with open(output_file_location, 'w', encoding= 'utf-8') as f:
                    f.write(str(output))
                
                print(f"\nScraped Sites count : {site_count}")
