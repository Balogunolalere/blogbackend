from gnews import GNews

google_news = GNews(language='en', country='NG', period='7d', max_results=5)

news = google_news.get_news('technology')

for article in news:
    print(f"Title: {article['title']}")
    print(f"URL: {article['url']}")
    print(f"Published: {article['published date']}")
    print('-' * 40)