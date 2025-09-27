import express from "express";
import path from "path";
import OpenAI from "openai";
import * as dotenv from "dotenv"; // Import dotenv

// Load environment variables from .env file
dotenv.config();

const app = express();
const PORT = parseInt(process.env.PORT || "5000", 10);

// Initialize OpenAI API
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Middleware to parse JSON bodies
app.use(express.json());

// Serve static files from the current directory (for index.html)
app.use(express.static("."));

// Serve client-side JavaScript from a 'public' directory
// We'll put our client.js here.
app.use("/public", express.static(path.join(__dirname, "public")));

// Route to serve the HTML file
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// --- NEW API ROUTE FOR CHAT ---
app.post("/api/chat", async (req, res) => {
  const { messages } = req.body;
  if (!messages) {
    return res.status(400).json({ error: "Missing messages in request body." });
  }

  // Define the system role to guide the AI for the interview
  const systemMessage = {
    role: "system",
    content: `You are a friendly, conversational AI assistant acting as a medical intake specialist. Your goal is to collect the following information from the user, one piece at a time: gender, age, height, weight, and medical history. Start by introducing yourself and asking for their gender. Keep your responses brief and conversational. Do not ask for all pieces of information at once.`,
  };

  try {
    const response = await openai.chat.completions.create({
      model: "gpt-3.5-turbo", // A fast and capable model for chat
      messages: [systemMessage, ...messages],
    });

    res.json(response.choices[0].message);
  } catch (error) {
    console.error("OpenAI API Error:", error);
    res.status(500).json({ error: "Failed to communicate with OpenAI API." });
  }
});
// -----------------------------

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Server is running on port ${PORT}`);
});
