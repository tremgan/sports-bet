
from sqlmodel import SQLModel, Session, select
from typing import Optional
from datetime import timedelta
from rapidfuzz import fuzz

from core.models import BookmakerMatch, BookmakerMatchCreate ,SportsBettingOdds, Match
from logger import logger

"""
This module is responsible for matching incoming bookmaker matches with existing matches in the database, 
or creating new matches if no good match is found. It uses a combination of exact matching and fuzzy string matching to find the best match for each incoming bookmaker match. 
The matching process is designed to be robust to minor differences in match labels and to allow for some flexibility in match datetimes.
"""


TIME_DELTA_FOR_MATCHING = timedelta(hours=1)
TOKEN_SORT_RATIO_THRESHOLD = 75

def find_match(bookmaker_match: BookmakerMatch, session: Session) -> Optional[Match]:
    """Find the best matching Match for a given BookmakerMatch, or return None if no good match is found."""
    
    logger.info(f"Starting match search for bookmaker match: {bookmaker_match.match_label} at {bookmaker_match.match_datetime}")
    
    time_window_start = bookmaker_match.match_datetime - TIME_DELTA_FOR_MATCHING
    time_window_end = bookmaker_match.match_datetime + TIME_DELTA_FOR_MATCHING


    candidates: list[Match] = session.exec(
        select(Match).where(
            Match.match_datetime >= time_window_start,
            Match.match_datetime <= time_window_end,
        )
    ).all()

    logger.info(f"Found {len(candidates)} candidate matches within time window")
    
    if not candidates:
        logger.info("No candidate matches found within time window")
        return None
    

    exact = next((c for c in candidates if c.match_label == bookmaker_match.match_label and c.match_datetime == bookmaker_match.match_datetime), None)
    # note that there could be multiple exact matches, 
    # however Matches have a unique constraint on (match_label, match_datetime) so there should be at most one exact match in the database
    if exact:
        logger.info(f"Found exact match: {exact.match_label} at {exact.match_datetime}")
        return exact
        
    # If no exact match, use fuzzy matching
    logger.info("No exact match found, performing fuzzy matching")
    best_candidate = max(candidates, key=lambda c: fuzz.token_sort_ratio(c.match_label, bookmaker_match.match_label))
    best_score = fuzz.token_sort_ratio(best_candidate.match_label, bookmaker_match.match_label)
    
    logger.info(f"Best fuzzy match: '{best_candidate.match_label}' with score {best_score}")

    # If the best score is above the threshold, return the best candidate, otherwise return None
    if best_score <= TOKEN_SORT_RATIO_THRESHOLD:
        logger.warning(f"Best match score {best_score} is below threshold {TOKEN_SORT_RATIO_THRESHOLD}, no match found")
        return None
    
    logger.info(f"Match found with score {best_score}: {best_candidate.match_label}")
    return best_candidate

def create_match_from_bookmaker_match(bookmaker_match: BookmakerMatch) -> Match:
    return Match(
        match_label=bookmaker_match.match_label,
        match_datetime=bookmaker_match.match_datetime,
        team1=bookmaker_match.match_label.split(' vs ')[0],
        team2=bookmaker_match.match_label.split(' vs ')[1],
    )
        

def run(session: Session):

    bookmaker_matches = session.exec(select(BookmakerMatch).where(BookmakerMatch.match_id == None, 
                                                                    BookmakerMatch.matching_attempts < 3)).all()
    for bookmaker_match in bookmaker_matches:
        match = find_match(bookmaker_match, session)
        if not match:
            # If no match found, create a new Match and link it to the BookmakerMatch
            match = create_match_from_bookmaker_match(bookmaker_match)
            session.add(match)
            session.flush()  # flush to get the new match ID

        bookmaker_match.match_id = match.id
        # Increment matching attempts
        bookmaker_match.matching_attempts += 1
        session.add(bookmaker_match)
        
        session.commit()


    
if __name__ == '__main__':

    from config import engine

    with Session(engine) as session:
        run(session)