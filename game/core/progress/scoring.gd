class_name Scoring
extends RefCounted


class Result:
	extends RefCounted
	var questions_correct: int = 0
	var questions_total: int = 0
	var identities_correct: int = 0
	var identities_total: int = 0
	var wrong_questions: Array[StringName] = []

	func score() -> float:
		var total := questions_total + identities_total
		return 0.0 if total == 0 else float(questions_correct + identities_correct) / total

	func solved() -> bool:
		return questions_total > 0 and questions_correct == questions_total


static func evaluate(case_data: CaseData, identities: Dictionary, answers: Dictionary) -> Result:
	var r := Result.new()
	for c in case_data.characters:
		r.identities_total += 1
		if String(identities.get(String(c.id), "")) == c.display_name:
			r.identities_correct += 1
	for q in case_data.questions:
		r.questions_total += 1
		if String(answers.get(String(q.id), "")) == q.answer:
			r.questions_correct += 1
		else:
			r.wrong_questions.append(q.id)
	return r
