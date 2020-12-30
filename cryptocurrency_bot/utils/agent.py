from fake_useragent import UserAgent, FakeUserAgentError


def get_useragent(): 
    """
    Get user agent for a nonblocking request

    :return: user_agent:str
    """
    try:
        return UserAgent().random  # get random useragent
    except FakeUserAgentError:
        # return basic useragent  
        return "Mozilla/5.0 \
               (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
               (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36"
