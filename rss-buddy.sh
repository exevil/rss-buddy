#!/bin/bash

# --- Parameter Initialization ---
# Initialize variables for parameters to store values from args or env vars
arg_api_key=""
arg_feeds=""
arg_days_lookback=""
arg_model=""
arg_max_tokens=""
arg_criteria=""
arg_output_dir=""
arg_generate_pages=false

# --- Argument Parsing ---
# Loop through command-line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --api-key)
            arg_api_key="$2"
            shift # past argument
            shift # past value
            ;;
        --feeds)
            arg_feeds="$2"
            shift # past argument
            shift # past value
            ;;
        --days-lookback)
            arg_days_lookback="$2"
            shift # past argument
            shift # past value
            ;;
        --model)
            arg_model="$2"
            shift # past argument
            shift # past value
            ;;
        --max-tokens)
            arg_max_tokens="$2"
            shift # past argument
            shift # past value
            ;;
        --criteria)
            arg_criteria="$2"
            shift # past argument
            shift # past value
            ;;
        --output-dir)
            arg_output_dir="$2"
            shift # past argument
            shift # past value
            ;;
        --pages)
            arg_generate_pages=true
            shift # past argument
            ;;
        *)    # unknown option
            # You might want to add error handling here for unknown args
            shift # past argument
            ;;
    esac
done

# --- Load Environment Variables (if needed) ---
# Load from .env file first if it exists and script is run locally
# Note: In GitHub Actions, env vars are already set, this helps local runs
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
fi

# --- Parameter Resolution (Arg -> Env Var Fallback) ---
# For each parameter, use the command-line arg value if provided,
# otherwise, fall back to the environment variable.
final_api_key="${arg_api_key:-$OPENAI_API_KEY}"
final_feeds="${arg_feeds:-$RSS_FEEDS}"
final_days_lookback="${arg_days_lookback:-$DAYS_LOOKBACK}"
final_model="${arg_model:-$AI_MODEL}"
final_max_tokens="${arg_max_tokens:-$SUMMARY_MAX_TOKENS}"
final_criteria="${arg_criteria:-$USER_PREFERENCE_CRITERIA}"
final_output_dir="${arg_output_dir:-${OUTPUT_DIR:-processed_feeds}}" # Default to 'processed_feeds' if both arg and OUTPUT_DIR env var are missing

# --- Validation ---
# Define required parameters and check if they have values
REQUIRED_PARAMS=("final_api_key" "final_feeds" "final_days_lookback" "final_model" "final_max_tokens" "final_criteria")
MISSING_PARAMS=()

for PARAM_VAR in "${REQUIRED_PARAMS[@]}"; do
    # Use indirect variable expansion to check the value of the final variable
    if [ -z "${!PARAM_VAR}" ]; then
        # Extract the original name (e.g., final_api_key -> api_key or OPENAI_API_KEY) for the error message
        ORIG_NAME=$(echo "$PARAM_VAR" | sed 's/^final_//' | tr '[:lower:]' '[:upper:]')
        if [[ "$ORIG_NAME" == "API_KEY" ]]; then ORIG_NAME="OPENAI_API_KEY"; fi
        if [[ "$ORIG_NAME" == "FEEDS" ]]; then ORIG_NAME="RSS_FEEDS"; fi
        if [[ "$ORIG_NAME" == "CRITERIA" ]]; then ORIG_NAME="USER_PREFERENCE_CRITERIA"; fi

        MISSING_PARAMS+=("--${ORIG_NAME,,} / \$${ORIG_NAME}")
    fi
done

# If any required parameters are missing, show an error and exit
if [ ${#MISSING_PARAMS[@]} -gt 0 ]; then
    echo "Error: The following required parameters are missing:"
    for PARAM in "${MISSING_PARAMS[@]}"; do
        echo "  - $PARAM"
    done
    echo ""
    echo "Please provide them via command-line arguments (e.g., --api-key 'value') or environment variables."
    exit 1
fi

# --- Execution ---
echo "Running rss-buddy..."

# Prepare the --generate-pages flag if needed
GENERATE_PAGES_FLAG=""
if [ "$arg_generate_pages" = true ]; then
    echo "Will generate GitHub Pages..."
    GENERATE_PAGES_FLAG="--generate-pages"
fi

# Execute the Python script with the final resolved parameters
# Ensure parameters with spaces/newlines are quoted
./run_rss_buddy.py \
    --api-key "$final_api_key" \
    --feeds "$final_feeds" \
    --days-lookback "$final_days_lookback" \
    --model "$final_model" \
    --max-tokens "$final_max_tokens" \
    --criteria "$final_criteria" \
    --output-dir "$final_output_dir" \
    $GENERATE_PAGES_FLAG

echo "Done!" 