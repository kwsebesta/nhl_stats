# ~/nhl-stats/nhl-venv/bin/ python
"""scrape.py scrapes the nhl website to download stats"""
import time
import requests


def get_game_boxscore(team_id, game_id):
    """Retrive boxscore stats for a team and game id"""
    game_url = "https://statsapi.web.nhl.com/api/v1/game/" + str(game_id) + "/boxscore"
    game_boxscore = requests.get(game_url).json()
    if game_boxscore["teams"]["home"]["team"]["id"] == team_id:
        boxscore_stats = game_boxscore["teams"]["home"]["teamStats"]["teamSkaterStats"]
        boxscore_stats["venue"] = "home"
    elif game_boxscore["teams"]["away"]["team"]["id"] == team_id:
        boxscore_stats = game_boxscore["teams"]["away"]["teamStats"]["teamSkaterStats"]
        boxscore_stats["venue"] = "away"
    else:
        print("Error: Team not found in game")
    return boxscore_stats


def get_team_stats(team_name):
    """Retrieve team stats for date range"""
    # Get teams
    teams = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json()
    # Search for specific teams
    for team in teams["teams"]:
        if team["name"] == team_name:
            team_id = team["id"]
            print(team_id)
    # Load season games
    # Choose dates in yyyy-mm-dd
    start_date = "2016-09-01"
    end_date = "2017-05-31"
    url = (
        "https://statsapi.web.nhl.com/api/v1/schedule?teamId="
        + str(team_id)
        + "&startDate="
        + start_date
        + "&endDate="
        + end_date
    )
    games = requests.get(url).json()
    # Get regular season games
    game_ids = [
        i["games"][0]["gamePk"]
        for i in games["dates"]
        if i["games"][0]["gamePk"] // 10 ** 4 % 10 == 2
    ]

    boxscore_stats = {}
    for game_id in game_ids:
        time.sleep(1)  # delay for 1 request/sec
        boxscore_stats[game_id] = get_game_boxscore(team_id=team_id, game_id=game_id)

    return boxscore_stats


if __name__ == "__main__":
    season_stats = get_team_stats("Chicago Blackhawks")
