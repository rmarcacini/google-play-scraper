import json
from time import sleep

from typing import Optional, Tuple, List

from google_play_scraper import Sort
from google_play_scraper.constants.element import ElementSpecs
from google_play_scraper.constants.regex import Regex
from google_play_scraper.constants.request import Formats
from google_play_scraper.utils.request import post
import pickle




MAX_COUNT_EACH_FETCH = 199


class _ContinuationToken:
    __slots__ = "token", "lang", "country", "sort", "count", "filter_score_with"

    def __init__(self, token, lang, country, sort, count, filter_score_with):
        self.token = token
        self.lang = lang
        self.country = country
        self.sort = sort
        self.count = count
        self.filter_score_with = filter_score_with


def _fetch_review_items(
    url: str,
    app_id: str,
    sort: int,
    count: int,
    filter_score_with: Optional[int],
    pagination_token: Optional[str],
):
    dom = post(
        url,
        Formats.Reviews.build_body(
            app_id,
            sort,
            count,
            "null" if filter_score_with is None else filter_score_with,
            pagination_token,
        ),
        {"content-type": "application/x-www-form-urlencoded"},
    )

    match = json.loads(Regex.REVIEWS.findall(dom)[0])

    return json.loads(match[0][2])[0], json.loads(match[0][2])[-1][-1]


def reviews(
    app_id: str,
    lang: str = "en",
    country: str = "us",
    sort: Sort = Sort.NEWEST,
    count: int = 100,
    filter_score_with: int = None,
    continuation_token: _ContinuationToken = None,
) -> Tuple[List[dict], _ContinuationToken]:
    if continuation_token is not None:
        token = continuation_token.token

        lang = continuation_token.lang
        country = continuation_token.country
        sort = continuation_token.sort
        count = continuation_token.count
        filter_score_with = continuation_token.filter_score_with
    else:
        token = None

    url = Formats.Reviews.build(lang=lang, country=country)

    if count > MAX_COUNT_EACH_FETCH:
        _count = MAX_COUNT_EACH_FETCH
    else:
        _count = count

    result = []

    while True:
        try:
            review_items, token = _fetch_review_items(
                url, app_id, sort, _count, filter_score_with, token
            )
        except (TypeError, IndexError):
            token = None
            break

        for review in review_items:
            result.append(
                {
                    k: spec.extract_content(review)
                    for k, spec in ElementSpecs.Review.items()
                }
            )

        remaining_count = count - len(result)

        if remaining_count == 0:
            break

        if isinstance(token, list):
            token = None
            break

        if remaining_count < 200:
            _count = remaining_count

    return (
        result,
        _ContinuationToken(token, lang, country, sort, count, filter_score_with),
    )


def reviews_all(app_id: str, data_dir: str, sleep_milliseconds: int = 0,  **kwargs) -> list:
    kwargs.pop("count", None)
    kwargs.pop("continuation_token", None)

    continuation_token = None

    result = []

    counter = 1
    while True:
        _result, continuation_token = reviews(
            app_id,
            count=MAX_COUNT_EACH_FETCH,
            continuation_token=continuation_token,
            **kwargs
        )

        #result += _result
        pickle.dump( _result, open( data_dir+"/"+str(counter)+'.pkl', "wb" ) )
        counter += 1

        if continuation_token.token is None:
            break

        if sleep_milliseconds:
            sleep(sleep_milliseconds / 1000)

    return result




