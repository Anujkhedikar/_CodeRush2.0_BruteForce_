document.getElementById('mentorForm').addEventListener('submit', async (event) => {
  event.preventDefault();

  const mode = document.getElementById('mode').value;
  const language = document.getElementById('language').value;
  const inputText = document.getElementById('inputText').value;
  const result = document.getElementById('result');

  result.textContent = 'Loading...';

  try {
    const response = await fetch('/mentor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, language, input_text: inputText }),
    });

    const data = await response.json();
    result.textContent = data.response || JSON.stringify(data, null, 2);
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
});
