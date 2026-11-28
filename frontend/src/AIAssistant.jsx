
import { useEffect, useRef, useState } from "react";
import axios from "axios";
import {
  Brain, Send, Bot, User, Sparkles,
  LoaderCircle, MessageCircle
} from "lucide-react";
import "./AIAssistant.css";

const API = "http://localhost:5000/api/ai";

function AIAssistant() {
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get(`${API}/history`, {
          withCredentials: true
        });

        const chats = response.data.history || [];

        setMessages(chats.flatMap(chat => [
          {
            id: `${chat.chat_id}-user`,
            role: "user",
            text: chat.user_message
          },
          {
            id: `${chat.chat_id}-ai`,
            role: "assistant",
            text: chat.ai_response
          }
        ]));
      } catch (error) {
        console.error("Unable to load chat history:", error);
      } finally {
        setHistoryLoading(false);
      }
    };

    fetchHistory();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth"
    });
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();

    const text = message.trim();

    if (!text || loading) return;

    setMessage("");
    setMessages(old => [
      ...old,
      {
        id: `user-${Date.now()}`,
        role: "user",
        text
      }
    ]);

    setLoading(true);

    try {
      const response = await axios.post(
        `${API}/chat`,
        { message: text },
        { withCredentials: true }
      );

      setMessages(old => [
        ...old,
        {
          id: `ai-${Date.now()}`,
          role: "assistant",
          text: response.data.ai_response
        }
      ]);
    } catch (error) {
      setMessages(old => [
        ...old,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          text: error.response?.data?.message ||
            "Sorry, I couldn't respond. Please try again."
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const suggestions = [
    "I'm feeling stressed",
    "Help me with my studies",
    "I feel low today",
    "Give me a motivation boost"
  ];

  return (
    <div className="ai-assistant-page">
      <div className="ai-assistant-header">
        <div className="ai-assistant-heading">
          <div className="ai-assistant-icon">
            <Brain size={25} />
          </div>
          <div>
            <h2>AI Wellbeing Assistant</h2>
            <p>Your supportive space to talk and reflect</p>
          </div>
        </div>

        <span className="ai-online-status">
          <span></span> Here to listen
        </span>
      </div>

      <div className="ai-chat-container">
        <div className="ai-chat-messages">
          {historyLoading ? (
            <div className="ai-empty-state">
              <LoaderCircle className="ai-spinner" size={28} />
              <p>Loading your conversations...</p>
            </div>
          ) : (
            <>
              {messages.length === 0 && (
                <div className="ai-welcome">
                  <div className="ai-welcome-icon">
                    <Sparkles size={30} />
                  </div>
                  <h3>Hello! Welcome to Serenify.</h3>
                  <p>
                    I'm here to listen and help you explore
                    ways to support your wellbeing.
                  </p>

                  <div className="ai-suggestions">
                    {suggestions.map((item, index) => (
                      <button
                        key={index}
                        type="button"
                        onClick={() => setMessage(item)}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map(item => (
                <div
                  key={item.id}
                  className={`ai-message ${
                    item.role === "user"
                      ? "ai-user-message"
                      : "ai-bot-message"
                  }`}
                >
                  <div className="ai-message-avatar">
                    {item.role === "user"
                      ? <User size={18} />
                      : <Bot size={18} />}
                  </div>

                  <div className="ai-message-content">
                    <span>
                      {item.role === "user" ? "You" : "Serenify Assistant"}
                    </span>
                    <p>{item.text}</p>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="ai-message ai-bot-message">
                  <div className="ai-message-avatar">
                    <Bot size={18} />
                  </div>
                  <div className="ai-message-content">
                    <span>Serenify Assistant</span>
                    <p className="ai-typing">
                      <LoaderCircle size={16} />
                      Thinking...
                    </p>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        <form className="ai-chat-input" onSubmit={sendMessage}>
          <input
            type="text"
            value={message}
            onChange={e => setMessage(e.target.value)}
            placeholder="Share what's on your mind..."
            disabled={loading || historyLoading}
          />

          <button
            type="submit"
            disabled={!message.trim() || loading || historyLoading}
            aria-label="Send message"
          >
            <Send size={19} />
          </button>
        </form>

        <p className="ai-disclaimer">
          <MessageCircle size={13} />
          Serenify offers general wellbeing support, not professional
          mental healthcare. If you're in immediate danger, contact
          local emergency services or someone you trust.
        </p>
      </div>
    </div>
  );
}

export default AIAssistant;
