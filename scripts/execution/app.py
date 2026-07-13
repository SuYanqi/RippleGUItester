import argparse
import os
import logging
from pathlib import Path

from src.pipelines.app import App
from src.pipelines.detector import BugReportTool
from src.pipelines.placeholder import Placeholder
from src.pipelines.executor import ComputerUseTool
from src.types.docker import DockerComputer
from src.utils.claude_util import ClaudeUtil
from src.utils.file_util import FileUtil
from src.utils.gpt_util import GPTUtil
from src.utils.path_util import PathUtil
from config import APP_NAME_FIREFOX, OUTPUT_DIR, DATA_DIR, APP_NAME_DESKTOP, APP_NAME_VSCODE, APP_NAME_ZETTLR, \
    APP_NAME_GODOT, APP_NAME_JABREF
from datetime import datetime

# Configure logging to show INFO and above with clear formatting
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run RippleGUItester on a specific repository")
    parser.add_argument(
        "--repo",
        type=str,
        choices=["Firefox", "Zettlr", "Godot", "JabRef"],
        default="Firefox",
        help="Repository name to test (default: Firefox)"
    )
    parser.add_argument(
        "--pr",
        type=int,
        help="Specific PR/bug number to test (optional, default: run all)"
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=None,
        help="Maximum number of test scenarios to execute per PR (e.g., --max-scenarios 1 to run only the first scenario). Default: run all scenarios."
    )
    args = parser.parse_args()

    # Map CLI argument (e.g., "Firefox") to internal config constant (e.g., "firefox")
    repo_map = {
        "Firefox": APP_NAME_FIREFOX,
        "Zettlr": APP_NAME_ZETTLR,
        "Godot": APP_NAME_GODOT,
        "JabRef": APP_NAME_JABREF
    }
    reponame = repo_map[args.repo]
    specific_pr = args.pr

    # Show simplified output
    print(f"\n{'='*70}")
    print(f"RippleGUItester - Testing {reponame}")
    if specific_pr:
        print(f"Target: PR #{specific_pr}")
    print(f"{'='*70}\n")

    # generator ##########################################
    generator_model = GPTUtil.GPT5_2

    with_change_desc = True
    with_change_intent = True
    # with_file_content = True
    with_file_content = False
    with_relevant_scenarios = True
    # with_relevant_scenarios = False
    with_cochange_file_content = False

    with_path_enhancement = True
    with_path_file_search = True
    # with_path_file_search = False
    with_data_enhancement = True

    # player ##########################################
    executor_model = ClaudeUtil.CLAUDE_OPUS_4_5  # best
    # executor_model = ClaudeUtil.CLAUDE_SONNET_4_5  # good
    # executor_model = ClaudeUtil.CLAUDE_HAIKU_4_5  # not okay
    instruction_reuse_tool_model= GPTUtil.GPT5_2
    use_instruction_reuse_tool = False
    use_extracted_executor_memory = True
    # use_extracted_executor_memory = False
    include_executor_history_image = False  # only applies when using conversation history (i.e., messages)

    # detector ##########################################
    detector_model = GPTUtil.GPT5_2

    # detector_reasoning_level = "high"
    detector_reasoning_level = "medium"
    # detector_reasoning_level = "low"
    # detector_reasoning_level = "minimal"
    with_detector_response = True

    # files_filename = "files"
    file_content_filename = "file_contents"
    scenarios_filename = "ranked_scenarios"
    if reponame == APP_NAME_FIREFOX:
        test_bugs_foldername = "test_bugs"
        test_bugs_filename = "test_bugs"
    else:
        test_bugs_foldername = "test_pulls"
        test_bugs_filename = "selected_test_pulls"  # filter prs not suitable for gui testing
    bugs = FileUtil.load_pickle(PathUtil.get_bugs_filepath(Path(reponame, test_bugs_foldername), f"{test_bugs_filename}"))
    # print(f"len({test_bugs_filename}): {len(bugs)}")
    computer_use_tool = ComputerUseTool().to_params()
    replay_wait_time = 3000
    if reponame == APP_NAME_GODOT:
        replay_wait_time = 9000
    bug_report_tool = None
    if detector_model[Placeholder.MODEL_NAME].startswith("claude"):
        bug_report_tool = BugReportTool().to_params()

    bugs = sorted(bugs, key=lambda bug: bug.id, reverse=True)

    # Filter by specific PR if provided
    if specific_pr is not None:
        if reponame == APP_NAME_FIREFOX:
            # Firefox: bug.id is already a number
            bugs = [bug for bug in bugs if bug.id == specific_pr]
        else:
            # GitHub repos: bug.id is a URL, extract number for comparison
            bugs = [bug for bug in bugs if bug.extract_number_from_github_url() == specific_pr]

        if not bugs:
            print(f"❌ Error: PR/bug #{specific_pr} not found in {reponame}")
            print(f"Available PRs: {sorted([b.id for b in FileUtil.load_pickle(PathUtil.get_bugs_filepath(Path(reponame, test_bugs_foldername), f'{test_bugs_filename}'))])[:10]}...")
            exit(1)
        # print(f"Running on specific PR/bug: #{specific_pr}")

    logging.info(f"Starting testing pipeline for {len(bugs)} PR(s)")

    for idx, bug in enumerate(bugs[0:], 1):
        if reponame == APP_NAME_FIREFOX:
            bug_id = bug.id
            input_filepath = Path(DATA_DIR, reponame, test_bugs_foldername, f"{bug.id}")
        else:
            bug_id = bug.extract_number_from_github_url()
        input_filepath = Path(DATA_DIR, reponame, test_bugs_foldername, f"{bug_id}")

        print(f"\n{'─'*70}")
        logging.info(f"Processing PR #{bug_id} ({idx}/{len(bugs)})")
        print(f"{'─'*70}")

        if with_file_content:
            # files = FileUtil.load_pickle(Path(input_filepath, f"{files_filename}.json"))
            # with_file_content = files
            file_contents_path = str(Path(input_filepath, f"{file_content_filename}.json"))

            vector_store_id = GPTUtil.create_vector_store([file_contents_path], vector_store_name=f"{bug.id}_{file_content_filename}")
            with_file_content = [vector_store_id]

        if with_relevant_scenarios:
            # logging.info("Loading ranked test scenarios")
            ranked_scenarios = FileUtil.load_json(Path(input_filepath, f"{scenarios_filename}.json"))
            with_relevant_scenarios = ranked_scenarios

        logging.info("Preparing output directory")
        foldername = f"{Placeholder.GENERATOR}_{generator_model[Placeholder.MODEL_NAME]}"
        if with_change_desc:
            foldername += f"_{Placeholder.CODE_CHANGE_DESCRIPTION}"
        if with_change_intent:
            foldername += f"_{Placeholder.CODE_CHANGE_INTENT}"
        if with_file_content:
            foldername += f"_{Placeholder.FILE_CONTENT}"
        if with_relevant_scenarios:
            foldername += f"_{Placeholder.PRECEDING_CHANGE_INTENTS}"
        if with_cochange_file_content:
            foldername += f"_{Placeholder.COCHANGE_FILE_CONTENT}"

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        foldername = foldername + f"_{timestamp}"

        # Create output structure: output/{repo}/output/{pr_id}/{generator_folder}
        output_filepath = Path(OUTPUT_DIR, reponame, "output", f"{bug_id}", foldername)
        # Check if the folder exists
        if not os.path.exists(output_filepath):
            # If it doesn't exist, create it
            os.makedirs(output_filepath)

        logging.info(f"Output directory: {output_filepath}")
        logging.info("Starting 3-phase pipeline: Generator → Executor → Detector")

        App.pipeline(bug, with_change_desc, with_change_intent, with_file_content, with_relevant_scenarios, generator_model,
                     with_path_enhancement, with_path_file_search, with_data_enhancement,
                     executor_model, instruction_reuse_tool_model,
                     computer_use_tool, replay_wait_time,
                     detector_model, bug_report_tool,
                     output_filepath, reponame,
                     use_instruction_reuse_tool=use_instruction_reuse_tool,
                     use_extracted_executor_memory=use_extracted_executor_memory,
                     include_executor_history_image=include_executor_history_image,
                     with_detector_response=with_detector_response,
                     detector_reasoning_level=detector_reasoning_level,
                     max_scenarios=args.max_scenarios)







