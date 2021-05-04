var timeout = 0;
var delay = 500;
var keywords = [];
var typing = false;
flask_http = (window.location.href.match(/127\.0\.0\.1/g)) ? "http://127.0.0.1:5000" : "https://alvelvis-chatbot.ejemplo.me/";

document.addEventListener("DOMContentLoaded", () => {
  const inputField = document.getElementById("input");
  inputField.addEventListener("keydown", (e) => {
    if (e.keyCode == 13 && inputField.value.trim().length > 0) {
      let input = inputField.value;
      inputField.value = "";
      output(input);
    }
  });

  $.ajax({
    url: flask_http,
    method: 'POST',
    data: {api_response: 'keywords'},
    success: function(data){
      keywords = data.api_response;
      addChat("", "Olá! Me pergunte sobre algo que eu respondo.");
      addChat("", "Quer saber tudo o que eu faço?");
  }});
  
  const queryString = window.location.search;
  const urlParams = new URLSearchParams(queryString);
  const q = urlParams.get('q')
  if (q) { input.value = decodeURI(q) };

});

function output(input) {
  addChat(input, "");
  window.history.pushState({}, "", window.location.href.split("/chatbot")[0] + "/chatbot/?q=" + encodeURI(input));
}

function addChat(input, product) {
  const messagesContainer = document.getElementById("messages");
    
  if (input.trim().length > 0) {
    let userDiv = document.createElement("div");
    userDiv.id = "user";
    userDiv.className = "user response";
    userDiv.innerHTML = `<img src="user.png" class="avatar"><span>${input}</span>`;
    messagesContainer.appendChild(userDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight - messagesContainer.clientHeight;
  };  

  $.post(flask_http, {'input': product.length > 0 ? "" : input}, function(data){
    timeout = timeout + delay;
    setTimeout(() => {
      typing = true;
      let botDiv = document.createElement("div");
      let botImg = document.createElement("img");
      let botText = document.createElement("span");
      botDiv.id = "bot";
      botImg.src = "bot-mini.png";
      botImg.className = "avatar";
      botDiv.className = "bot response";
      botText.innerText = "Digitando...";
      botDiv.appendChild(botText);
      botDiv.appendChild(botImg);
      messagesContainer.appendChild(botDiv);
      // Keep messages at most recent
      messagesContainer.scrollTop = messagesContainer.scrollHeight - messagesContainer.clientHeight;
           
      product = product.length > 0 ? product : data.bot_response;
      
      // Fake delay to seem "real"
      setTimeout(() => {
        timeout = timeout - delay
        botText.innerText = `${product}`;
        for (kw of keywords) {
          if (botText.innerText.toLowerCase().indexOf(kw[0].toLowerCase()) != -1) {
            botText.innerHTML = botText.innerHTML.replace(kw[0], `<a reply="${kw[1]}" class="write-this">${kw[0]}</a>`)
          }
        }
        $('.write-this').unbind('click').click(function() { writeThis($(this).attr('reply')) });
        textToSpeech(product);
        typing = false;
        messagesContainer.scrollTop = messagesContainer.scrollHeight - messagesContainer.clientHeight;
      }, delay);
      
    }, timeout);
  });
}

function writeThis(data) {
  output(data);
};
