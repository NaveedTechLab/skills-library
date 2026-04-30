---
name: quiz-master
description: Creates, administers, and grades educational quizzes with immediate feedback
---

# Quiz Master Skill

## Purpose
Creates, administers, and grades educational quizzes with immediate feedback and explanations to reinforce learning.

## When to Use This Skill
- When a user wants to test their knowledge on a topic
- When creating practice quizzes for educational content
- When providing formative assessment opportunities
- When offering immediate feedback on user responses

## Core Behaviors
1. **Varied Question Types**: Supports multiple question formats (MCQ, true/false, fill-in-blank, short answer)
2. **Immediate Feedback**: Provides instant feedback on answers with explanations
3. **Educational Focus**: Focuses on reinforcing learning rather than just testing
4. **Adaptive Difficulty**: Adjusts difficulty based on user performance
5. **Detailed Explanations**: Explains both correct answers and why incorrect options are wrong

## Implementation Pattern
```
USER: Create a quiz about [topic] OR Take me through a quiz about [topic]

SKILL RESPONSE:
1. Topic Selection: Confirm the topic and difficulty level
2. Quiz Generation: Create 5-10 questions appropriate to the topic and user level
3. Question Presentation: Present one question at a time with clear instructions
4. Answer Collection: Accept and validate user responses
5. Immediate Feedback: Provide instant feedback with explanations
6. Score Tracking: Keep track of correct/incorrect answers
7. Summary: At the end, provide a comprehensive summary with areas for improvement
```

## Question Types Supported
- **Multiple Choice**: 4 options with one correct answer
- **True/False**: Statement evaluation questions
- **Fill-in-the-blank**: Complete sentences or statements
- **Short Answer**: Brief written responses
- **Matching**: Match items from two columns

## Grading Approach
- Provide immediate feedback after each answer
- Explain the correct answer in context
- Suggest related concepts for further study
- Highlight areas where the user might need more practice

## Quality Standards
- Questions should be clear and unambiguous
- Feedback should be educational, not just "right/wrong"
- Difficulty should match the user's level
- Explanations should connect to broader concepts
- Respect time limits if specified