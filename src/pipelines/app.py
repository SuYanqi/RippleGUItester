import logging
import os
from pathlib import Path
from tqdm import tqdm
from src.pipelines.detector import Detector
from src.pipelines.executor import Executor
from src.pipelines.generator import Generator
from src.pipelines.placeholder import Placeholder


class App:
    def __init__(self):
        pass

    @staticmethod
    def pipeline(bug, with_change_desc, with_change_intent, with_file_content, with_relevant_scenarios, generator_model,
                 with_path_enhancement, with_path_file_search, with_data_enhancement,
                 executor_model, instruction_reuse_tool_model,
                 computer_use_tool, replay_wait_time,
                 detector_model, bug_report_tool,
                 output_filepath, reponame,
                 use_instruction_reuse_tool=False,
                 use_extracted_executor_memory=True,
                 include_executor_history_image=False, with_detector_response=True,
                 detector_reasoning_level='medium',
                 max_scenarios=None):

        # generator ################################################################################################
        print(f"\n{'='*70}")
        logging.info("PHASE 1/3: Generator - Generating test scenarios")
        print(f"{'='*70}")
        generator_messages, generator_output = (
            Generator.generate_test_scenarios(bug,
                                              with_change_desc=with_change_desc,
                                              with_change_intent=with_change_intent,
                                              with_file_content=with_file_content,
                                              with_relevant_scenarios=with_relevant_scenarios,
                                              model=generator_model,
                                              with_path_enhancement=with_path_enhancement,
                                              with_path_file_search=with_path_file_search,
                                              with_data_enhancement=with_data_enhancement,
                                              output_filepath=output_filepath,
                                              reponame=reponame, ))

        # executor and detector ################################################################################################
        test_scenario_index = 0
        build_info = generator_messages[2]["content"][Placeholder.INFO][Placeholder.BUILD_INFO]

        test_scenarios = generator_output[Placeholder.SCENARIOS]
        if max_scenarios is not None:
            test_scenarios = test_scenarios[:max_scenarios]
        logging.info(f"Generated {len(test_scenarios)} test scenarios")

        code_change_intent = ""
        for one_content in generator_messages[1]["content"][Placeholder.CODE_CHANGE_INTENT]:
            code_change_intent += f"{one_content[Placeholder.SUMMARY]}\n"
        change_intent_explanation = generator_messages[2]["content"][Placeholder.CHANGE_INTENT_EXPLANATION]

        print(f"\n{'='*70}")
        logging.info(f"PHASE 2/3: Executor - Running {len(test_scenarios)} test scenario(s)")
        print(f"{'='*70}")

        for index, test_scenario in tqdm(enumerate(test_scenarios[test_scenario_index:]), desc="Test Scenarios"):
            index = test_scenario_index + index
            index_output_filepath = Path(output_filepath, f"{index}")
            if not os.path.exists(index_output_filepath):
                # If it doesn't exist, create it
                os.makedirs(index_output_filepath)
            logging.info(f"Scenario {index+1}/{len(test_scenarios)}: Executing test scenario")
            replay_output = Executor.execute_test_scenario(build_info, test_scenario, index_output_filepath,
                                                           computer_use_tool=computer_use_tool,
                                                           use_instruction_reuse_tool=use_instruction_reuse_tool,
                                                           use_extracted_executor_memory=use_extracted_executor_memory,
                                                           include_executor_history_image=include_executor_history_image,
                                                           instruction_reuse_tool_model=instruction_reuse_tool_model,
                                                           executor_model=executor_model,
                                                           replay_wait_time=replay_wait_time)

            logging.info(f"Scenario {index+1}/{len(test_scenarios)}: Detecting bugs")
            if replay_output is None:
                logging.warning(f"Scenario {index+1}: Execution failed, skipping detection")
                continue
            Detector.detect_bugs(code_change_intent=code_change_intent, change_intent_explanation=change_intent_explanation,
                                 replay_output=replay_output,
                                 detector_model=detector_model, index_output_filepath=index_output_filepath,
                                 bug_report_tool=bug_report_tool, with_response=with_detector_response,
                                 reasoning=detector_reasoning_level)

