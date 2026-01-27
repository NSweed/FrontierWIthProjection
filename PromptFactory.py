PROBLEM_PROJECTION_PREFIX = "I'm being asked the following but I don't understand anything about {}. Explain what these are like I'm in middle school, and frame the questions in the same way. \n"
PROJECTION_ANSWERING_PREFIX = "Now answer all the questions you have reframed using the same, middle-school vocab style approach"
GRADING_ANSWER_PREFIX = "Here is an answer to a question, and a rubric for grading it. grade the answer using the rubric.\n Answer: "
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

class PromptFactory:

    @staticmethod
    def get_default_answer_prompt(problem_dict):
        return clean_problem(problem_dict["problem"], remove_cot=False)

    @staticmethod
    def get_projection_prompt(problem_dict):
        problem = clean_problem(problem_dict["problem"])
        return f"{PROBLEM_PROJECTION_PREFIX.format(problem_dict['subject'])} \n{problem}"

    @staticmethod
    def get_reprojection_prompt(projected_answer):
        return f"{PROBLEM_REPROJECTION_PREFIX} {projected_answer}"

    @staticmethod
    def get_projection_answer_prompt():
        return PROJECTION_ANSWERING_PREFIX



