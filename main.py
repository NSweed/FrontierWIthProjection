import json
from ChatSession import  ChatSession
import os
from openai import OpenAI
import time
from random import shuffle
GRADING_MODEL= "gpt-5"
from PromptFactory import PromptFactory

FULL_PATH = ""
PROBLEM_REFORMATION_PREFIX = "I'm being asked the following but I don't understand anything about material/life sciences. Explain what these are like I'm in middle school, and frame the questions in the same way. \n"
PROJECTION_ANSWERING_PREFIX = "Now answer all the questions you have reframed using the same, middle-school vocab style approach"
GRADING_ANSWER_PREFIX = "Here is an answer to a question, and a rubric for grading it. grade the answer using the rubric.\n Answer:\n"
PROBLEM_REPROJECTION_PREFIX = "Here is a middle-school-vocabulary answer to a question.  looking at the question and the answer, flesh out and articulate a full and detailed answer to the question using scientific vocabulary and \"uncompressing\" ideas that were simplified in the middle-school version."


GRADING_TEMPLATE = "You are grading a science exam.\n\
You will be given the problem, attempted answer, and a rubric to grade the answer. The rubric \
will total up to 10 points.\n\
Evaluate the attemped answer against the provided rubric. Pay close attention to detail and \
grade it strictly, but fairly. Only evaluate against the rubric, as you yourself should not make \
any judgements (e.g., even if you think the answer is correct but rubric is wrong, you should \
treat the rubric as the gold standard). Return the absolute total number of points earned (it can \
be a decimal based on the rubric). *** \n\
The problem: {problem} \
***\n\
The rubric: {rubric}\
***\n\
The attempted answer: {answer}\
***\n\n\
First, think step-by-step about each rubric item. Explain your reasoning for each rubric item. \
Then, tally the points up and write VERDICT: ¡total˙points¿ in the last line of your response, \
no other text. For example, VERDICT: 2.5 or VERDICT: 8."


problems = []
with open("test.json", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            problems.append(json.loads(line))

    x = 1




def grade_answer_from_file(grading_prompt_func,fname, problem_d, save_prefix):
    from pathlib import Path
    filename = Path(fname).name
    with open(fname, encoding="utf-8") as f:
        answer = f.read()
        full_problem = problem_d["problem"]
        problem = clean_problem(full_problem)
        rubric = problem_d["answer"]
        default_grade_save_path = os.path.join("Responses", "Grading from files", f"{save_prefix}_high_reasoning_{filename}")
        default_grade_full_chat_path = os.path.join("FullChats", f"{save_prefix}_file_grading_{filename}")
        grade_answer_high_reasoning(grading_prompt_func,problem, answer, rubric, default_grade_save_path,
                                    default_grade_full_chat_path)

def get_and_save_response(chat, prompt, save_path, force_search = False):
    time.sleep(100)
    response = chat.send_message(prompt, force_search=force_search)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(response)
    return response

def clean_problem(raw_text, remove_cot = True):
    # 1. Remove the "Context:" and "Question:" labels
    # We use .replace() for simple targeted removals
    cleaned = raw_text.replace("Context:", "").replace("Question:", "")
    if not remove_cot:
        return cleaned
    # 2. Cut off everything starting from "Think step by step"
    # We split the text into two parts at that marker and keep only the first part [0]
    marker = "Think step by step"
    if marker in cleaned:
        cleaned = cleaned.split(marker)[0]

    # 3. Strip leading/trailing whitespace and newlines
    return cleaned.strip()




def answer_question_based_on_projection(chat, answer_projection_text, response_save_path):
    return get_and_save_response(chat,answer_projection_text, response_save_path)

def ask_problem_projection(chat, problem_text, projection_prompt_function, response_save_path):
    chat_prompt = projection_prompt_function(problem_text)
    return get_and_save_response(chat, chat_prompt, response_save_path)

def get_problem_projection_pipeline(chat,problem, save_suffix, projection_prompt_func, project_answer_prompt_func, force_search = False):
    print("\t1. projecting problem")
    simplification_response_save_path = os.path.join("Responses", "Simplification", save_suffix)
    ask_problem_projection(chat, problem, projection_prompt_func, simplification_response_save_path)
    #answering projected problem:
    print("\t2. answering projection")
    projection_answer_path = os.path.join("Responses", "Projection Answer", save_suffix)
    projection_answer_prompt = project_answer_prompt_func()
    projection_answer = get_and_save_response(chat, projection_answer_prompt,  projection_answer_path, force_search=force_search)

    return projection_answer, chat

def get_problem_reprojection(chat, problem_projection, reprojection_prompt_func, save_suffix, force_search = False):
    prompt  = reprojection_prompt_func(problem_projection)
    return get_and_save_response(chat, prompt, save_suffix, force_search=force_search)


def full_pipeline(problem_d, id_count, provider, model_name, **kwargs):
    # Extract defaults from kwargs
    api_key = kwargs.get("api_key", "")
    grade_projected = kwargs.get("grade_projected", True)
    grade_default = kwargs.get("grade_default", True)
    grade_reprojected = kwargs.get("grade_reprojected", True)
    clean_chat = kwargs.get("clean_chat", False)
    keep_chat = kwargs.get("keep_chat", True)
    web_enabled = kwargs.get("web_enabled", False)
    high_reasoning = kwargs.get("high_reasoning", True)
    force_search = kwargs.get("force_search", False)
    projection_prompt_func = kwargs.get("projection_prompt_func", PromptFactory.get_projection_prompt)
    reprojection_prompt_func = kwargs.get("reprojection_prompt_func", PromptFactory.get_reprojection_prompt)
    project_answer_prompt_func = kwargs.get("projection_answer_prompt_func", PromptFactory.get_projection_answer_prompt)
    grading_prompt_func = kwargs.get("grading_prompt_func", PromptFactory.get_grading_prompt)

    #small definitions
    subject = problem_d["subject"]
    full_problem = problem_d["problem"]
    problem = clean_problem(full_problem)
    rubric = problem_d["answer"]
    web_text = "web_enabled" if web_enabled else "web_disabled"
    save_suffix = f"{provider}_{model_name}_{subject}_{id_count}_{web_text}.txt"
    #initializing chat
    chat = ChatSession(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        web_enabled=web_enabled,
        high_reasoning=high_reasoning,
    )
    projection_histories = []
    #getting problem projection:
    if grade_projected:

        print("Projecting problem to lower space")
        problem_projection = get_problem_projection_pipeline(chat, problem, projection_prompt_func,project_answer_prompt_func, save_suffix)
        projection_histories.append(chat.get_history())
        #grading:
        print("Grading projected problem")
        projection_grade_save_path  = os.path.join("Responses", "Grading projection", save_suffix)
        projection_grade_full_chat_path = os.path.join("FullChats", f"projection_grading_{save_suffix}")
        grade_answer_high_reasoning(grading_prompt_func,problem,problem_projection, rubric, projection_grade_save_path, projection_grade_full_chat_path)
        if not keep_chat:
            projection_hist_path = os.path.join("FullChats", f"projection_chat_{save_suffix}")
            write_history(projection_hist_path, [chat.get_history()])
        # grading_chat.save_history(projection_hist_path)

        #grading reprojected:
        if grade_reprojected:
            if keep_chat:
                print("Answering problem using projected answer - unclean chat")
                time.sleep(100)
                reprojection_path = os.path.join("Responses", "Reprojection", save_suffix)
                reprojected_answer = get_problem_reprojection(chat, problem_projection, reprojection_prompt_func, reprojection_path, force_search=force_search)
                projection_histories.append(chat.get_history())
                # saving history:
                projection_hist_path = os.path.join("FullChats", f"reprojection_cont_chat_{save_suffix}")
                write_history(projection_hist_path, [chat.get_history()])

                # grading
                print("Grading reprojection")
                time.sleep(100)
                reprojection_grade_save_path = os.path.join("Responses", "Grading from projection", save_suffix)
                reprojection_grade_full_chat_path = os.path.join("FullChats", f"reprojection_grading_{save_suffix}")
                grade_answer_high_reasoning(grading_prompt_func,problem, reprojected_answer, rubric, reprojection_grade_save_path,reprojection_grade_full_chat_path)


            if clean_chat:
                chat = ChatSession(
                    provider=provider,
                    model_name=model_name,
                    api_key=api_key,
                    web_enabled=web_enabled,
                    high_reasoning=high_reasoning,
                )
            print("Answering problem using projected answer - clean chat")
            time.sleep(100)
            reprojection_path  = os.path.join("Responses", "Reprojection", f"clean_{save_suffix}")
            reprojected_answer = get_problem_reprojection(chat, problem_projection, reprojection_prompt_func, reprojection_path, force_search=force_search)
            projection_hist_path = os.path.join("FullChats", f"reprojection_clean_chat_{save_suffix}")
            write_history(projection_hist_path, [chat.get_history()])
            #grading
            print("Grading reprojection")
            reprojection_grade_save_path = os.path.join("Responses", "Grading from projection", f"{save_suffix}_clean")
            reprojection_grade_full_chat_path = os.path.join("FullChats", f"clean_reprojection_grading_{save_suffix}")
            time.sleep(100)
            grade_answer_high_reasoning(grading_prompt_func,problem, reprojected_answer, rubric, reprojection_grade_save_path,reprojection_grade_full_chat_path)
            #reprojection_hist_path = os.path.join("FullChats", f"reprojection_grading_{save_suffix}")

    #grading regular:
    if grade_default:
        chat = ChatSession(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            web_enabled=web_enabled,
            high_reasoning=high_reasoning,
        )
        # get
        print("Getting default answer")
        time.sleep(100)
        default_problem = clean_problem(full_problem, False)
        default_save_path = os.path.join("Responses", "DefaultAnswers", save_suffix)
        default_answer = get_and_save_response(chat, default_problem, default_save_path, force_search=force_search)
        projection_hist_path = os.path.join("FullChats", f"default_answer_chat_{save_suffix}")
        write_history(projection_hist_path, [chat.get_history()])
        #grading:
        time.sleep(100)
        print("Grading default answer")
        default_grade_save_path = os.path.join("Responses", "Grading default", f"high_reasoning_{save_suffix}")
        default_grade_full_chat_path = os.path.join("FullChats", f"default_grading_{save_suffix}")
        grade_answer_high_reasoning(grading_prompt_func,problem, default_answer, rubric, default_grade_save_path, default_grade_full_chat_path)
        #reprojection_hist_path = os.path.join("FullChats", f"default_grading_{save_suffix}")
        #grading_chat.save_history(reprojection_hist_path)
    #chat.save_history(history_path)


def write_history(save_path, histories):
    with open(save_path,"w", encoding="utf-8") as f:
        for history in histories:
            for line in history:
                f.write(f"********** {line['role']} ********** \n\n")
                f.write(f"\t {line['content']}\n\n")
                f.write("---------------------------------------------------\n\n")



def get_high_reasoning_response(client, prompt):
    COST_INPUT = 1.25 / 1_000_000
    COST_CACHED = 0.125 / 1_000_000  # 90% discount
    COST_OUTPUT = 10.00 / 1_000_000

    response = client.responses.create(
        model="gpt-5",
        reasoning={"effort": "high"},
        text={"verbosity": "high"},
        input=[{"role": "user", "content": prompt}]
    )

    usage = response.usage

    # 1. Calculate Input Cost (Standard vs Cached)
    total_input = usage.input_tokens
    cached_input = usage.input_tokens_details.cached_tokens
    standard_input = total_input - cached_input

    input_cost = (standard_input * COST_INPUT) + (cached_input * COST_CACHED)

    # 2. Calculate Output Cost (Visible + Reasoning)
    total_output = usage.output_tokens
    reasoning_tokens = usage.output_tokens_details.reasoning_tokens
    visible_tokens = total_output - reasoning_tokens

    output_cost = total_output * COST_OUTPUT

    # 3. Final Calculation
    total_cost = input_cost + output_cost

    print(f"--- Cost Breakdown ---")
    print(f"Input: {standard_input} standard, {cached_input} cached")
    print(f"Output: {visible_tokens} visible, {reasoning_tokens} reasoning")
    print(f"TOTAL COST: ${total_cost:.6f}")

    return response.output_text

def grade_answer(chat, problem, answer, rubric, response_save_path, grade_from_template = True):
    if grade_from_template:
        prompt = GRADING_TEMPLATE.format(problem=problem, rubric = rubric, answer=  answer)
    else:
        prompt = f"{GRADING_ANSWER_PREFIX} {answer} \n Rubric:\n {rubric}\n"
    return get_and_save_response(chat, prompt, response_save_path)

def grade_answer_high_reasoning(grading_prompt_func,problem, answer, rubric, response_save_path, history_path):
    prompt = grading_prompt_func(problem, rubric, answer)
    grading_chat = ChatSession(
        provider="openai",
        model_name="gpt-5",
        api_key=api_key,
        web_enabled=False,
        high_reasoning=True
    )
    # get
    grade = get_and_save_response(grading_chat, prompt, response_save_path)
    write_history(history_path, [grading_chat.get_history()])
    return grade



def sample_different_problem_types(n, problems):
    type_to_count = {}
    problems_to_return = []
    for problem in problems:
        type = problem["subject"]
        if type not in type_to_count:
            type_to_count[type] = 0
        if type_to_count[type] < n:
            problems_to_return.append(problem)
            type_to_count[type] += 1
    return problems_to_return


def grade_answers_from_directory(grading_prompt_func,dir_name, problem_d, save_prefix):
    for file in os.listdir(dir_name):
        file_path = os.path.join(dir_name, file)
        print(f"starting with file {file_path}")
        grade_answer_from_file(grading_prompt_func,file_path, problem_d, save_prefix)

# 1. Setup your session (Change "openai" to "claude" or "gemini" as needed)

# 2. Start the conversation
type_to_id = {"physics" :0, "chemistry":0, "biology":0}
id_start = 200
shuffle(problems)
sampled_problems = sample_different_problem_types(3, problems)
# ,
options = [ ("anthropic", "claude-opus-4-5-20251101", True),
           ("anthropic", "claude-opus-4-5-20251101", False), ("openai", "gpt-5.2", False), ("openai", "gpt-5.2", True)]
options = [("anthropic", "claude-opus-4-5-20251101", True)]

# options = [ ("openai", "gpt-5.2", True)]



dir = os.path.join("Nikki Answers", "ours_runs", "same_claude_chat")
dir = "Nikki Answers"


api_key=os.environ.get("OPENAI_API_KEY")

chem_problem = problems[30]



model = "claude-opus-4-5-20251101"
provider = "anthropic"

grade_answers_from_directory(PromptFactory.get_grading_prompt, dir, chem_problem,  "nikki_answers")

# for i in range(5):
#     print(f"Starting with #{i}")
#     full_pipeline(chem_problem,  i+id_start, provider =provider, model_name=model, grade_projected=True, grade_reprojected=True,
#                   grade_regular=False, keep_chat=True, clean_chat=True, api_key=api_key, web_enabled=True, force_search = True)
#     print(f"Finished with #{i}")


pipeline_args = {
    "api_key": "",
    "grade_projected": True,
    "grade_default": True,
    "grade_reprojected": True,
    "clean_chat": False,
    "keep_chat": True,
    "web_enabled": False,
    "high_reasoning": True,
    "force_search": False,
    "provider": provider,
    "model_name": model
}

#
# for i,problem_d in enumerate(sampled_problems):
#     print(f"Starting with #{i}")
#     full_pipeline(problem_d, i + id_start, **pipeline_args)
#     print(f"Finished with #{i}")

# get_problem_projection_pipeline(problems[0], id_count, provider ="openai", model_name="gpt-5-nano")