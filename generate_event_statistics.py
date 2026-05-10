import argparse
import requests
import pandas as pd
import sys
import numpy as np

ftc_scout_api_url = "https://api.ftcscout.org/rest/v1"

def fetch_match_data(season, event_code):
    match_url = f"{ftc_scout_api_url}/events/{season}/{event_code}/matches/"
    return fetch_data(match_url)
    
def fetch_rankings_data(season, event_code):
    rankings_url = f"{ftc_scout_api_url}/events/{season}/{event_code}/matches/rankings"
    return fetch_data(rankings_url)

def fetch_teams_data(season, event_code):
    teams_url = f"{ftc_scout_api_url}/events/{season}/{event_code}/teams"
    return fetch_data(teams_url)


def fetch_data(url):
    try:
        response = requests.get(url)
        data = response.json()
        print(f"Successfully fetched data from: {url}")
        return data
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occured: {e.__cause__}")
        sys.exit()
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error occured: {e.__cause__}")
        sys.exit()
        return None
    
def get_args():
    parser = argparse.ArgumentParser(description="FTC Scout Data Downloader")
    parser.add_argument("--season", type=int, help="The season year (e.g., 2025)")
    parser.add_argument("--event", type=str, help="The event code (e.g., FTCCMP1EDIS)")
    parser.add_argument("--penalties", type=str, help="Inlcude penalties (yes, no)")
    
    args = parser.parse_args()

    # include penalties

    if not args.season:
        args.season = int(input("Enter Season Year (e.g. 2025): "))
    if not args.event:
        args.event = input("Enter Event Code (e.g. FTCCMP1EDIS): ").upper()
    if not args.penalties:
        args.penalties = input("Inlcude penalties (yes, no): ").lower()

    return args

def get_team_list(match_data):
    unique_teams = set()
        
    for match in match_data:
        if 'teams' in match:
            for team_entry in match['teams']:
                num = team_entry.get('teamNumber')
                if num:
                    unique_teams.add(num)
        
        team_list = sorted(list(unique_teams))
        return team_list
    
def get_alliance_teams_in_match(match, alliance):
    return [t['teamNumber'] for t in match['teams'] if t['alliance'] == alliance]

def get_alliance_score(match, alliance, include_penalties):
    if include_penalties:
        points_key = 'totalPoints'
    else:
        points_key = 'totalPointsNp'

    return match['scores'][alliance][points_key]

def build_base_matrices(number_of_teams, team_number_index, match_data, include_penalties):
    """
    Step 1: Loop through match data ONCE to build the baseline 
    alliance indicator matrix (A) and raw score vector (b).
    
    A_base shape: (2 * num_matches, number_of_teams)
    b_base shape: (2 * num_matches,)
    """
    num_matches = len(match_data)
    A_base = np.zeros((2 * num_matches, number_of_teams))
    b_base = np.zeros(2 * num_matches)

    for idx, match in enumerate(match_data):
        # Preserve original casing from your helper functions
        red_teams = get_alliance_teams_in_match(match, 'Red')
        blue_teams = get_alliance_teams_in_match(match, 'Blue')
        
        red_score = get_alliance_score(match, 'red', include_penalties)
        blue_score = get_alliance_score(match, 'blue', include_penalties)

        # Even rows (0, 2, 4...) represent the Red alliance
        red_row_idx = 2 * idx
        for t in red_teams:
            A_base[red_row_idx, team_number_index[t]] = 1
        b_base[red_row_idx] = red_score

        # Odd rows (1, 3, 5...) represent the Blue alliance
        blue_row_idx = 2 * idx + 1
        for t in blue_teams:
            A_base[blue_row_idx, team_number_index[t]] = 1
        b_base[blue_row_idx] = blue_score

    return A_base, b_base


def solve_ridge(A, b, team_number_index, lambda_reg=10):
    """
    Step 2: A generic Ridge Regression solver that maps 
    the solved matrix back to team IDs.
    """
    number_of_teams = len(team_number_index)
    I = np.eye(number_of_teams)
    
    # Solve the system: (A^T * A + lambda * I) * x = A^T * b
    values = np.linalg.solve(
        A.T @ A + lambda_reg * I, 
        A.T @ b
    )
    
    # Map back to team ID using the dict's explicit index mapping
    return {team_id: round(values[idx], 2) for team_id, idx in team_number_index.items()}


# --- Metric Specific Calculators (No Loops!) ---

def calculate_epa(A_base, b_base, team_number_index, lambda_reg=10):
    """
    Transforms the base matrices into margin-based matrices and solves for EPA.
    """
    # Slice out even rows (Red) and odd rows (Blue)
    red_rows = A_base[0::2]
    blue_rows = A_base[1::2]
    
    # EPA Design Matrix: Own alliance (1), Opponent alliance (-1)
    A_margin = np.zeros_like(A_base)
    A_margin[0::2] = red_rows - blue_rows  # Red perspective
    A_margin[1::2] = blue_rows - red_rows  # Blue perspective
    
    # EPA Target Vector: Own score - Opponent score
    red_scores = b_base[0::2]
    blue_scores = b_base[1::2]
    
    b_margin = np.zeros_like(b_base)
    b_margin[0::2] = red_scores - blue_scores
    b_margin[1::2] = blue_scores - red_scores
    
    return solve_ridge(A_margin, b_margin, team_number_index, lambda_reg)


def calculate_opr(A_base, b_base, team_number_index, lambda_reg=2):
    """
    Solves OPR directly using the raw alliance matrices.
    (OPR typically uses less regularization, e.g., lambda = 1 or 2)
    """
    return solve_ridge(A_base, b_base, team_number_index, lambda_reg)


def calculate_sos(A_base, metric_dict, team_number_index):
    """
    Calculates Strength of Schedule (SoS) for all teams using the pre-built A_base matrix.
    Works instantly for EPA, OPR, or any other team-level metric dict.
    """
    number_of_teams = len(team_number_index)
    
    # 1. Map the dictionary metrics into a flat NumPy array matching our matrix columns
    metric_vector = np.zeros(number_of_teams)
    for team_id, idx in team_number_index.items():
        metric_vector[idx] = metric_dict.get(team_id, 0.0)
        
    # 2. Build the opponent matrix by swapping even (Red) and odd (Blue) rows of A_base
    A_opp = np.zeros_like(A_base)
    A_opp[0::2] = A_base[1::2]  # Red's opponents are Blue
    A_opp[1::2] = A_base[0::2]  # Blue's opponents are Red
    
    # 3. Vectorized Math:
    # Get the sum of opponent metrics per alliance-match
    opp_sum_per_alliance_match = A_opp @ metric_vector
    # Attribute those sums back to the teams who played in those matches
    total_opp_sum_per_team = A_base.T @ opp_sum_per_alliance_match
    
    # Count the number of opponents faced per alliance-match (usually 3)
    opp_count_per_alliance_match = A_opp @ np.ones(number_of_teams)
    # Attribute those counts back to the teams
    total_opp_count_per_team = A_base.T @ opp_count_per_alliance_match
    
    # 4. Calculate the average opponent metric (avoiding division by zero)
    with np.errstate(divide='ignore', invalid='ignore'):
        sos_values = np.where(
            total_opp_count_per_team > 0, 
            total_opp_sum_per_team / total_opp_count_per_team, 
            0.0
        )
        
    # Map back to team IDs
    return {team_id: round(sos_values[idx], 2) for team_id, idx in team_number_index.items()}

def create_csv_file(dict, name):
    data_frame = pd.DataFrame(dict)
    data_frame.to_csv(f"{name}.csv", index=False)

def get_statistics(season, event, include_penalties):
    match_data = fetch_match_data(season, event)
    teams_data = fetch_teams_data(season, event)

    team_numbers = [team['teamNumber'] for team in teams_data]

    number_of_teams = len(team_numbers)
    team_number_index = {team_id: i for i, team_id in enumerate(team_numbers)}

    #use args for playoff include
    filtered_matches = [m for m in match_data if m.get('hasBeenPlayed') and m.get('tournamentLevel') == "Quals"]

    A_base, b_base = build_base_matrices(number_of_teams, team_number_index, filtered_matches, include_penalties)
    epa_data = calculate_epa(A_base, b_base, team_number_index, lambda_reg=10)
    opr_data = calculate_opr(A_base, b_base, team_number_index, lambda_reg=2)

    epa_sos_data = calculate_sos(A_base, epa_data, team_number_index)
    opr_sos_data = calculate_sos(A_base, opr_data, team_number_index)


    final_stats = []
    for team in teams_data:
        t_id = team['teamNumber']

        stats = team.get('stats', {})

        if (stats is None):
            continue

        scout_opr_data = stats.get('opr')
        avg = stats.get('avg', {})
        rank = stats.get('rank')

        scout_opr = scout_opr_data.get("totalPoints")

        averagePoints =  avg.get('totalPointsNp')
        rankingPoints = stats.get('rp')
        tb1_points = stats.get('tb1')

        epa = epa_data.get(t_id, 0)
        opr = opr_data.get(t_id, 0)
        
        epa_sos = epa_sos_data.get(t_id, 0)
        opr_sos = opr_sos_data.get(t_id, 0)

        final_stats.append({
            'Team': t_id,
            'Rank': rank,
            'Ranking Points': rankingPoints,
            "Average Points NP (Tie Breaker 1)": tb1_points,
            'EPA': epa,
            'OPR': opr,
            'FTCScout OPR': scout_opr,
            'EPA SOS': epa_sos,
            'OPR SOS': opr_sos,
            'Includes Penalties': include_penalties
        })
    return final_stats

def main():
    args = get_args()
    include_penalties = args.penalties == "yes"

    statistics = get_statistics(args.season, args.event, include_penalties)

    create_csv_file(statistics, f"output/{args.season}_{args.event}_statistics")
    print(f"Saved stats to CSV file!")

if __name__ == "__main__":
    main()