import ollama
import re

def ai_review(abstract_text):
    # Use Ollama for AI review
    try:
        prompt = f"""
        Evaluate this hackathon abstract on the following criteria:
        - Idea Creativity: How original and innovative is the idea?
        - Content Quality: How well-written and comprehensive is the abstract?
        - Practical Applicability: How feasible and practical is the solution?

        Provide scores out of 10 for each criterion and overall feedback.

        Abstract: {abstract_text}

        Format your response as:
        Idea Creativity: [score]
        Content Quality: [score]
        Practical Applicability: [score]
        Feedback: [detailed feedback]
        """
        response = ollama.generate(model='llama3:latest', prompt=prompt)
        result = response['response']
        
        # Parse the response to extract scores and feedback
        scores = {}
        feedback = ""
        lines = result.split('\n')
        for line in lines:
            line = line.strip()
            if 'Idea Creativity:' in line:
                scores['idea_creativity'] = float(re.search(r'\d+(\.\d+)?', line).group())
            elif 'Content Quality:' in line:
                scores['content_quality'] = float(re.search(r'\d+(\.\d+)?', line).group())
            elif 'Practical Applicability:' in line:
                scores['practical_applicability'] = float(re.search(r'\d+(\.\d+)?', line).group())
            elif 'Feedback:' in line:
                feedback = line.split(':', 1)[1].strip()
        
        # Ensure all scores are present, default to 5 if missing
        scores.setdefault('idea_creativity', 5.0)
        scores.setdefault('content_quality', 5.0)
        scores.setdefault('practical_applicability', 5.0)
        
        total_score = sum(scores.values()) / len(scores)
        return {
            'scores': scores,
            'total_score': total_score,
            'feedback': feedback or "Evaluation completed."
        }
    except Exception as e:
        # Fallback to mock scores
        return {
            'scores': {'idea_creativity': 7.5, 'content_quality': 8.0, 'practical_applicability': 7.0},
            'total_score': 7.5,
            'feedback': f"Error with Ollama: {str(e)}. Using demo mode."
        }
