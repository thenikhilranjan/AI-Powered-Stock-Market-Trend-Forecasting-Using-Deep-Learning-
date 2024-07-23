import concurrent.futures
import datetime
import time

# sentiment analysis libraries
import nltk
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from nltk.sentiment.vader import SentimentIntensityAnalyzer

nltk.downloader.download('vader_lexicon')

nifty_500_ticker_url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
nifty_500 = pd.read_csv(nifty_500_ticker_url)
nifty_500.to_csv('./datasets/NIFTY_500.csv')

nifty_200_ticker_url = 'https://archives.nseindia.com/content/indices/ind_nifty200list.csv'
nifty_200 = pd.read_csv(nifty_200_ticker_url)
nifty_200.to_csv('./datasets/NIFTY_200.csv')

nifty_100_ticker_url = 'https://archives.nseindia.com/content/indices/ind_nifty100list.csv'
nifty_100 = pd.read_csv(nifty_100_ticker_url)
nifty_100.to_csv('./datasets/NIFTY_100.csv')

nifty_50_ticker_url = 'https://archives.nseindia.com/content/indices/ind_nifty50list.csv'
nifty_50 = pd.read_csv(nifty_50_ticker_url)
nifty_50.to_csv('./datasets/NIFTY_50.csv')

# Set universe
universe = nifty_500

# Read CSV & create a tickers df
tickers_df = universe[['Symbol', 'Company Name']]
tickers_list = tickers_df['Symbol']

# News URL
news_url = 'https://ticker.finology.in/company/'
special_symbols = {
    'L&TFH': 'SCRIP-220350',
    'M&M' : 'SCRIP-100520',
    'M&MFIN': 'SCRIP-132720'
}

# Header for sending requests
header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'
    }
# list to store article data
article_data = []

# list to store tickers for which data is unavailable
unavailable_tickers = []

# function to fetch news and meta concurrently
def get_url_content(ticker):
    _ticker = special_symbols[ticker] if ticker in special_symbols.keys() else ticker
    url = '{}/{}'.format(news_url, _ticker)
    response = requests.get(url, headers=header)
    soup = BeautifulSoup(response.content, 'lxml')
    return ticker, soup
    
# function to parse news data and create a df
def ticker_article_fetch(i, ticker, soup):
    print('Fetching Article')
    news_links = soup.select('#newsarticles > a')
    if len(news_links) == 0:
        print('No news found for {}'.format(ticker))
        return True
    ticker_articles_counter = 0
    for link in news_links:
        art_title = link.find('span', class_='h6').text
        # separate date and time from datetime object
        date_time_obj = datetime.datetime.strptime(
            link.find('small').text, '%d %b %Y, %I:%M%p')
        art_date = date_time_obj.date().strftime('%Y/%m/%d')
        art_time = date_time_obj.time().strftime('%H:%M')
        article_data.append([ticker, art_title, art_date, art_time])
        ticker_articles_counter += 1
    print('No of articles: {}'.format(ticker_articles_counter))

start_time = time.time()
# send multiple concurrent requests using concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = [executor.submit(get_url_content, ticker)
               for ticker in tickers_list]
    for i, future in enumerate(concurrent.futures.as_completed(results)):
        ticker, soup = future.result()
        print(i, ticker)
        ticker_article_response = ticker_article_fetch(i, ticker, soup)
        if ticker_article_response:
            unavailable_tickers.append(ticker)
            print('skipping meta check for {}'.format(ticker))
            continue
end_time = time.time()

# calculate and print the time taken to send requests
time_taken = end_time - start_time
print("Time taken to send requests: {:.2f} seconds".format(time_taken))

# create df from article_data
articles_df = pd.DataFrame(article_data, columns=['Ticker', 'Headline', 'Date', 'Time'])

# create df from metadata
ticker_meta_df = pd.read_csv('./datasets/ticker_metadata.csv')

# Sentiment Analysis
print('Performing Sentiment Analysis')
vader = SentimentIntensityAnalyzer()

# import custom lexicon dictionary
lex_fin = pd.read_csv('./datasets/lexicon_dictionary.csv')
# create a dictionary from df columns
lex_dict = dict(zip(lex_fin.word, lex_fin.sentiment_score))
#set custom lexicon dictionary as default to calculate sentiment analysis scores
vader.lexicon = lex_dict

# Perform sentiment Analysis on the Headline column of all_news_df
# It returns a dictionary, transform it into a list
art_scores_df = pd.DataFrame(articles_df['Headline'].apply(vader.polarity_scores).to_list())

# Merge articles_df with art_scores_df
# merging on index, hence both indices should be same
art_scores_df = pd.merge(articles_df, art_scores_df,left_index=True, right_index=True)

# export article data to csv file
art_scores_df.to_csv('./datasets/NIFTY_500_Articles.csv')
