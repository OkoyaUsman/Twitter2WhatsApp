import os
import sys
import re
import json
import random
import logging
import requests
import validators
import urllib.parse
from time import sleep
from datetime import datetime
from selenium import webdriver
from curl_cffi import requests as req
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable logging for cleaner output
logging.disable(logging.CRITICAL)

# Bot configuration
USERNAME = os.getenv('TWITTER_USERNAME', '') # Twitter username to monitor
ID = os.getenv('TWITTER_USER_ID', '')  # Twitter user ID
BROWSER = None  # Selenium browser instance
WAIT = None  # WebDriverWait instance
PATH = os.path.dirname(os.path.abspath(__file__))  # Current directory path
VIDEO_LIMIT = 16777216  # Maximum video size for WhatsApp (16MB)
FILE_LIMIT = 104857600  # Maximum file size for WhatsApp (100MB)
profile_path = os.getenv('CHROME_PROFILE_PATH', '')  # Chrome profile path

# Twitter API credentials
auth_token = os.getenv('TWITTER_AUTH_TOKEN', '')
ct0 = os.getenv('TWITTER_CT0', '')

# Chrome options configuration
options = Options()
options.add_argument('--log-level=3')
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument(f"--user-data-dir={profile_path}")
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

# Initialize Chrome browser
BROWSER = webdriver.Chrome(service=Service(os.getenv('CHROMEDRIVER_PATH', '')), options=options)
BROWSER.get("https://web.whatsapp.com/")
WAIT = WebDriverWait(BROWSER, 20)

# WhatsApp authentication check
try:
    WAIT.until(EC.presence_of_element_located((By.XPATH, '//div[@title="Chats"]')))
except:
    print("Failed to login WhatsApp, launch in headful mode to reauthenticate.")
    sleep(30)
    exit()
print("WhatsApp Authentication OK!")

def main():
    """Main function that runs the bot's core functionality"""
    
    # Load video database and last processed tweet ID
    video_db = load_data("videos.json", {})
    lastfile = open("lastid.txt", "r")
    since_id = int(lastfile.readline())
    lastfile.close()
    
    # Initialize Twitter API clients
    api = TwitterAPI(token=auth_token, ct0=ct0)
    guest_api = TwitterAPI()
    
    while True:
        currentphone = ""
        log("Checking for new mentions...")
        tweets, since_id = api.getNotifications(since_id)
        
        for tweet in tweets:
            try:
                # Skip if not a reply
                if tweet["in_reply_to_status_id_str"] is None:
                    log("Not a reply, skipping")
                    continue
                
                # Extract tweet information
                tweetid = str(tweet["in_reply_to_status_id_str"])
                tweetuserid = str(tweet["user_id_str"])
                t_username = tweet["user_data"]["screen_name"]
                followed_by = tweet["user_data"]["followed_by"]
                
                log(f"@{t_username} mentioned @{USERNAME}")
                
                # Process video request
                if f"@{USERNAME}" in str(tweet["full_text"]).lower() and str(tweet["in_reply_to_user_id_str"]) != ID:
                    if not followed_by:
                        log("User not following us")
                    
                    # Check user registration
                    # Your API endpoint or mechanism to get a user's phone number.
                    server = requests.post("https://yourwebsite.com/getUserPhone", 
                                        data={'id': tweetuserid}).json()
                    requester_phone = str(server["phone"])
                    requester_username = str(server["username"])
                    
                    if requester_phone == "NULL":
                        log("User not registered")
                        continue
                    
                    if requester_phone.isdigit():
                        # Extract frame number from request
                        match = re.search(r"frame([1-4])", str(tweet["full_text"]).lower())
                        frame_number = int(match.group(1)) if match else 1
                        
                        localId = f"{tweetid}_{frame_number}"
                        
                        # Check if video is in database
                        if localId in video_db:
                            log(f"Found {tweetid} video in db")
                            video_url = video_db[localId]["url"]
                            videotype = video_db[localId]["type"]
                        else:
                            log(f"Fresh {tweetid} video")
                            video_url, videotype = guest_api.getVideo(tweetid, frame_number)
                            if video_url and videotype:
                                video_db[localId] = {"url": video_url, "type": videotype}
                                save_data(video_db, "videos.json")
                        
                        if video_url == "large":
                            log("Too large even for WhatsApp")
                            continue
                            
                        if validators.url(video_url):
                            log("@"+requester_username+" phone is: +"+requester_phone)
                            
                            # Download video
                            r = requests.get(video_url, allow_redirects=True, stream=True)
                            file = "temp/"+tweetid+".mp4"
                            with open(file, "wb") as vid:
                                for chunk in r.iter_content(chunk_size=1024):
                                    if chunk:
                                        vid.write(chunk)
                                        vid.flush()
                            
                            # Send video to WhatsApp
                            if requester_phone == currentphone:
                                log("Chat already opened, sending")
                            elif contact_exists("@"+requester_username, "+"+requester_phone):
                                log("Found contact in list, sending")
                            else:
                                log("Opening new chat")
                                BROWSER.get(f"https://web.whatsapp.com/send?phone={requester_phone}&text&type=phone_number&app_absent=1")
                                sleep(3)
                            
                            send("Hi @"+requester_username+", Your requested video from Twitter is ready here:\n\nMake money with your twitter account on adxpot.com", 
                                file, requester_phone, videotype)
                            currentphone = requester_phone
                    else:
                        log("Invalid phone number format")
                else:
                    log("Not a valid mention")
            except Exception as e:
                log("Error on line {} - {}".format(sys.exc_info()[-1].tb_lineno, e))
                sleep(10)
        
        # Update last processed tweet ID
        lastfile2 = open("lastid.txt", "w")
        lastfile2.write(str(since_id))
        lastfile2.close()
        
        log("Completed a batch and wiping temp folder...t2w")
        sleep(60)
        delete_folder_contents("temp/")

def delete_folder_contents(folder_path):
    """Delete all contents of a folder"""
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            os.rmdir(dir_path)
    return True

def load_data(file_name="data.json", empty=[]):
    """Load data from JSON file"""
    f = os.path.join(PATH, file_name)
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    else:
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(empty, file)
        return empty

def save_data(data, file_name="data.json"):
    """Save data to JSON file"""
    f = os.path.join(PATH, file_name)
    with open(f, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

def send(message, video, mobile, videotype, trial=2):
    """Send message and video to WhatsApp"""
    try:
        msgbox = WAIT.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p')))
        filename = os.path.realpath(video)
        msgbox.send_keys(message)
        msgbox.send_keys(Keys.ENTER)
        WAIT.until_not(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]//*[@data-icon="msg-time"]')))
        log(f"Message sent successfully to +{mobile}")
        
        clipButton = WAIT.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div[1]/div/button/span')))
        clipButton.click()
        
        if videotype == "video":
            video_button = WAIT.until(EC.presence_of_element_located((By.XPATH, '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]')))
            video_button.send_keys(filename)
            sendButton = WAIT.until(EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Send"]')))
            sendButton.click()
            sleep(3)
            WAIT.until_not(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]//*[@data-icon="msg-time"]')))
            log(f"Video MP4 has been successfully sent to +{mobile}")
        elif videotype == "file":
            file_button = WAIT.until(EC.presence_of_element_located((By.XPATH, '//input[@accept="*"]')))
            file_button.send_keys(filename)
            sendButton = WAIT.until(EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Send"]')))
            sendButton.click()
            sleep(5)
            WAIT.until_not(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]//*[@data-icon="msg-time"]')))
            log(f"Video File has been successfully sent to +{mobile}")
    except Exception as e:
        log(f"Couldn't send, we will retry. {trial}/3 {e}")

def contact_exists(contact, phone):
    """Check if contact exists in WhatsApp"""
    try:
        search_box = WAIT.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[3]/div/div[3]/div/div[1]/div/div[2]/div[2]/div/div/p')))
        search_box.clear()
        search_box.send_keys(contact)
        sleep(2)
        search_box.send_keys(Keys.ENTER)
        sleep(1)
        opened_chat = WAIT.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[3]/div/div[4]/div/header/div[2]/div/div/div/span')))
        title = opened_chat.text
        if title.strip().lower() == contact.strip().lower() or title.replace(" ", "").strip() == phone.strip():
            search_cancel_button = WAIT.until(EC.presence_of_element_located((By.XPATH, '//span[@data-icon="x-alt"]')))
            search_cancel_button.click()
            return True
        else:
            return False
    except Exception as bug:
        log(f"Could not find {contact}")
        return False

def log(*msg):
    """Log messages to file and console"""
    with open(os.path.join(PATH, "log.txt"), 'a') as log:
        log.write('[{:%d/%m/%Y - %H:%M:%S}] {}\n'.format(datetime.now(), *msg))
    print('[{:%d/%m/%Y - %H:%M:%S}] {}'.format(datetime.now(), *msg))

class TwitterAPI:
    """Twitter API client class"""
    def __init__(self, token="", ct0=""):
        self.session = requests.Session()
        self.notification_url = "https://x.com/i/api/2/notifications/mentions.json?include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&include_ext_is_blue_verified=1&include_ext_verified_type=1&include_ext_profile_image_shape=1&skip_status=1&cards_platform=Web-12&include_cards=1&include_ext_alt_text=true&include_ext_limited_action_results=true&include_quote_count=true&include_reply_count=1&tweet_mode=extended&include_ext_views=true&include_entities=true&include_user_entities=true&include_ext_media_color=true&include_ext_media_availability=true&include_ext_sensitive_media_warning=true&include_ext_trusted_friends_metadata=true&send_error_codes=true&simple_quoted_tweet=true&count=20&requestContext=launch&ext=mediaStats%2ChighlightedLabel%2ChasParodyProfileLabel%2CvoiceInfo%2CbirdwatchPivot%2CsuperFollowMetadata%2CunmentionInfo%2CeditControl%2Carticle"
        
        headers = {
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "origin": "https://x.com",
            "referer": "https://x.com/",
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
            "x-csrf-token": ct0,
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome"
        }
        cookies = {
            "auth_token": token,
            "ct0": ct0
        }
        self.session.headers.update(headers)
        self.session.cookies.update(cookies)

    def getGuestTweetDetails(self, tweet_id):
        """Get tweet details using guest token"""
        try:
            session = req.Session(impersonate=random.choice(["chrome99_android", "chrome"]))
            proxy = os.getenv('PROXY_URL', '')
            session.proxies.update({"http": proxy, "https": proxy})
            headers = {
                'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                'origin': 'https://x.com',
                'referer': 'https://x.com/',
                'X-Twitter-Active-User': 'yes',
                'X-Twitter-Client-Language': 'en',
            }
            session.headers.update(headers)
            query_tweet = "taYqW6MhmUrkLfkp6vlXgw"
            
            guest_token = session.post("https://api.twitter.com/1.1/guest/activate.json").json()["guest_token"]
            features = {
                "rweb_lists_timeline_redesign_enabled": True,
                "premium_content_api_read_enabled": False,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                "responsive_web_grok_analyze_post_followups_enabled": False,
                "responsive_web_grok_share_attachment_enabled": True,
                "profile_label_improvements_pcf_label_in_post_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_enhance_cards_enabled": False,
                "rweb_video_timestamps_enabled": True,
                "rweb_tipjar_consumption_enabled": True,
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "articles_preview_enabled": True,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "tweet_with_visibility_results_prefer_gql_media_interstitial_enabled": False
            }
            variables = {
                "withCommunity": False,
                "includePromotedContent": False,
                "withVoice": False,
                "focalTweetId": tweet_id,
                "tweetId": tweet_id
            }
            fieldToggles = {
                "withArticleRichContentState": True,
                "withArticlePlainText": False,
                "withGrokAnalyze": False,
                "withDisallowedReplyControls": False
            }
            url = f"https://api.x.com/graphql/{query_tweet}/TweetResultByRestId?variables={urllib.parse.quote(json.dumps(variables))}&features={urllib.parse.quote(json.dumps(features))}&fieldToggles={urllib.parse.quote(json.dumps(fieldToggles))}"
            session.headers.update({"x-guest-token": guest_token})
            details = session.get(url)
            max_retries = 5
            cur_retry = 0
            while details.status_code == 400 and cur_retry < max_retries:
                details = session.get(url)
                cur_retry += 1
            assert details.status_code == 200, f'Failed to get tweet details. Status code: {details.status_code}. Tweet: {tweet_id}. Query: {query_tweet}'
            return details.json()
        except Exception as e:
            log(f"ErrorGuest: {e}")
            return {}
        
    def getTweetDetails(self, tweet_id):
        """Get tweet details using authenticated session"""
        try:
            features = {
                "rweb_lists_timeline_redesign_enabled": True,
                "premium_content_api_read_enabled": False,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                "responsive_web_grok_analyze_post_followups_enabled": True,
                "responsive_web_grok_share_attachment_enabled": True,
                "profile_label_improvements_pcf_label_in_post_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_enhance_cards_enabled": False,
                "rweb_video_timestamps_enabled": True,
                "rweb_tipjar_consumption_enabled": True,
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "articles_preview_enabled": True,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "tweet_with_visibility_results_prefer_gql_media_interstitial_enabled": False,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
            }
            fieldToggles = {
                "withArticleRichContentState": True,
                "withArticlePlainText": False,
                "withGrokAnalyze": False,
                "withDisallowedReplyControls": False
            }
            variables = {
                "focalTweetId": tweet_id,
                "with_rux_injections": False,
                "includePromotedContent": True,
                "withCommunity": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withBirdwatchNotes": True,
                "withVoice": True,
                "rankingMode": "Relevance"
            }
            url = f"https://api.x.com/graphql/LG_-V6iikp5XQKoH1tSg6A/TweetDetail?variables={urllib.parse.quote(json.dumps(variables))}&features={urllib.parse.quote(json.dumps(features))}&fieldToggles={urllib.parse.quote(json.dumps(fieldToggles))}"
            details = self.session.get(url)
            max_retries = 5
            cur_retry = 0
            while details.status_code == 400 and cur_retry < max_retries:
                details = self.session.get(url)
                cur_retry += 1
            assert details.status_code == 200, f'Failed to get tweet details. Status code: {details.status_code}. Tweet: {tweet_id}'
            return details.json()
        except:
            return {}

    def getVideo(self, tweet_id, target) -> str:
        """Get video URL from tweet"""
        video_url = ""
        videotype = ""
        resp = self.getGuestTweetDetails(tweet_id)
        try:
            if resp:
                if "result" in resp["data"]["tweetResult"]:
                    if "legacy" in resp["data"]["tweetResult"]["result"]:
                        if "extended_entities" in resp["data"]["tweetResult"]["result"]["legacy"]:
                            if "media" in resp["data"]["tweetResult"]["result"]["legacy"]["extended_entities"]:
                                medias = resp["data"]["tweetResult"]["result"]["legacy"]["extended_entities"]["media"]
                                if "video_info" in medias[target-1]:
                                    variants = [v for v in medias[target-1]["video_info"]["variants"] if 'bitrate' in v]
                                    if variants:
                                        variants.sort(key=lambda x: x['bitrate'], reverse=True)
                                        variant = variants[0]
                                        response = requests.head(variant['url'], allow_redirects=True)
                                        if 'Content-Length' in response.headers:
                                            if int(response.headers['Content-Length']) < VIDEO_LIMIT:
                                                video_url = variant['url']
                                                videotype = "video"
                                            elif int(response.headers['Content-Length']) < FILE_LIMIT:
                                                video_url = variant['url']
                                                videotype = "file"
                                            else:
                                                video_url = "large"
                                                videotype = "large"
                    elif "reason" in resp["data"]["tweetResult"]["result"]:
                        if resp["data"]["tweetResult"]["result"]["reason"] == "NsfwLoggedOut":
                            log("NSFW Video, trying alternative")
                            resp = self.getTweetDetails(tweet_id)
                            for u in resp["data"]["threaded_conversation_with_injections_v2"]["instructions"]:
                                if u["type"] == "TimelineAddEntries":
                                    for k in u["entries"]:
                                        try:
                                            if "tweet-" in k["entryId"]:
                                                result = k["content"]["itemContent"]["tweet_results"]["result"]
                                                if "legacy" in result:
                                                    if result["legacy"]["id_str"] == tweet_id:
                                                        if "extended_entities" in result["legacy"]:
                                                            if "media" in result["legacy"]["extended_entities"]:
                                                                medias = result["legacy"]["extended_entities"]["media"]
                                                                if "video_info" in medias[target-1]:
                                                                    variants = [v for v in medias[target-1]["video_info"]["variants"] if 'bitrate' in v]
                                                                    if variants:
                                                                        variants.sort(key=lambda x: x['bitrate'], reverse=True)
                                                                        variant = variants[0]
                                                                        response = requests.head(variant['url'], allow_redirects=True)
                                                                        if 'Content-Length' in response.headers:
                                                                            if int(response.headers['Content-Length']) < VIDEO_LIMIT:
                                                                                video_url = variant['url']
                                                                                videotype = "video"
                                                                            elif int(response.headers['Content-Length']) < FILE_LIMIT:
                                                                                video_url = variant['url']
                                                                                videotype = "file"
                                                                            else:
                                                                                video_url = "large"
                                                                                videotype = "large"
                                                        break
                                        except:
                                            pass
        except Exception as e:
            log(f"Error: {e}")
        return video_url, videotype

    def getNotifications(self, since_id):
        """Get new notifications from Twitter"""
        tweets = []
        response = self.session.get(self.notification_url)
        if response.status_code == 200:
            data = response.json()
            if "tweets" in data['globalObjects'] and "users" in data['globalObjects']:
                tweet_data = data['globalObjects']['tweets']
                user_data = data['globalObjects']['users']
                alltweets = sorted(tweet_data.keys())
                for thing in alltweets:
                    tweet = tweet_data[thing]
                    tid = int(tweet["id_str"])
                    tweet["user_data"] = user_data[tweet["user_id_str"]]
                    if since_id < tid:
                        since_id = tid
                        tweets.append(tweet)
            else:
                log("No new data")
            for index, instruction in enumerate(data["timeline"]["instructions"]):
                if "addEntries" in instruction:
                    if len(data["timeline"]["instructions"][index]["addEntries"]["entries"]) > 0:
                        new_cursor_value = data["timeline"]["instructions"][index]["addEntries"]["entries"][0]["content"]["operation"]["cursor"]["value"]
                        parsed_url = urlparse(self.notification_url)
                        query_parameters = parse_qs(parsed_url.query)
                        query_parameters["cursor"] = [new_cursor_value]
                        encoded_query_parameters = urlencode(query_parameters, doseq=True)
                        self.notification_url = urlunparse(parsed_url._replace(query=encoded_query_parameters))
                        break
        else:
            log(f"Failed to get latest notifications: {response.status_code}")
        return tweets, since_id
    
if __name__ == '__main__':
    main()