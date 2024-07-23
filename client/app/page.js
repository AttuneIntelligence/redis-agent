"use client";
import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import Image from 'next/image';
import { Send } from 'lucide-react';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import Head from 'next/head';

export default function Chat() {
  const [userInput, setUserInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoadingResponse, setIsLoadingResponse] = useState(false);
  const chatContainerRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  useEffect(() => {
    adjustTextareaHeight();
  }, [userInput]);

  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  const handleUserInput = async () => {
    if (isLoadingResponse || !userInput.trim()) return;
    setIsLoadingResponse(true);
    const newMessage = { role: 'user', content: userInput.trim() };

    const JSON_TO_SERVER = {
      "user_id": '0123456789',
      "display_name": "user",
      "question": userInput.trim()
    };

    setChatHistory((prevChat) => [...prevChat, newMessage]);
    setUserInput('');

    try {
      const response = await fetch('http://localhost:5001/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(JSON_TO_SERVER),
      });

      const reader = response.body.getReader();
      let assistantMessageContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        let chunk = new TextDecoder().decode(value);
        if (chunk.includes('[DONE]')) {
          chunk = chunk.replace('[DONE]', '');
        }
        assistantMessageContent += chunk;
        setChatHistory((prevChat) => {
          const updatedChat = [...prevChat];
          const lastMessageIndex = updatedChat.length - 1;
          if (updatedChat[lastMessageIndex]?.role === 'assistant') {
            updatedChat[lastMessageIndex].content = assistantMessageContent;
          } else {
            updatedChat.push({ role: 'assistant', content: assistantMessageContent });
          }
          return updatedChat;
        });
      }
    } catch (error) {
      console.error("Error fetching response from server:", error);
    } finally {
      setIsLoadingResponse(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleUserInput();
    }
  };

  return (
    <>
      <Head>
        <title>Redis Agent</title>
      </Head>
      <div className="bg-gray-100 min-h-screen flex flex-col justify-center items-center p-4">
        <div className="w-full max-w-4xl bg-white rounded-lg shadow-lg overflow-hidden">
          <div
            className="h-[calc(100vh-200px)] overflow-y-auto p-12"
            ref={chatContainerRef}
          >
            {chatHistory.map((message, index) => (
              <div
                key={index}
                className={`flex items-start mb-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start max-w-[80%]`}>
                  <div className="w-8 h-8 rounded-full flex-shrink-0 relative">
                    <Image
                      src={message.role === 'user' ? '/user-image-icon.jpg' : '/ai_image.png'}
                      alt={`${message.role} profile`}
                      fill
                      className="rounded-full object-cover"
                      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    />
                  </div>
                  <div className={`mx-2 p-3 rounded-lg ${message.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-black'}`}>
                    <ReactMarkdown
                      className="prose max-w-none"
                      components={{
                        code({ node, inline, className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || '');
                          return !inline && match ? (
                            <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className={className} {...props}>
                              {children}
                            </code>
                          );
                        },
                        a: ({ children, href, ...props }) => {
                          // Check if the href is an external link
                          const isExternal = href && !href.startsWith('/') && !href.startsWith('#') && !href.includes('localhost');
                          return isExternal ? (
                            <a {...props} href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
                              {children}
                            </a>
                          ) : null;
                        },
                        p: ({ children, ...props }) => (
                          <p {...props} className="mb-2">
                            {children}
                          </p>
                        ),
                        h1: ({ children, ...props }) => (
                          <h1 {...props} className="text-3xl font-bold mb-2">
                            {children}
                          </h1>
                        ),
                        h2: ({ children, ...props }) => (
                          <h2 {...props} className="text-2xl font-bold mb-2">
                            {children}
                          </h2>
                        ),
                        h3: ({ children, ...props }) => (
                          <h3 {...props} className="text-xl font-bold mb-2">
                            {children}
                          </h3>
                        ),
                        h4: ({ children, ...props }) => (
                          <h4 {...props} className="text-lg font-bold mb-2">
                            {children}
                          </h4>
                        ),
                        h5: ({ children, ...props }) => (
                          <h5 {...props} className="text-base font-bold mb-2">
                            {children}
                          </h5>
                        ),
                        h6: ({ children, ...props }) => (
                          <h6 {...props} className="text-sm font-bold mb-2">
                            {children}
                          </h6>
                        ),
                        sup: ({ children, ...props }) => (
                          <sup {...props} className="align-super">
                            {children}
                          </sup>
                        ),
                        emoji: ({ children, ...props }) => (
                          <span {...props} className="emoji">
                            {children}
                          </span>
                        ),
                      }}
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="border-t p-4">
            <div className="flex items-end">
              <textarea
                ref={textareaRef}
                placeholder="Ask me anything..."
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none text-black"
                rows="1"
                style={{ minHeight: '44px', maxHeight: '120px' }}
              />
              <button
                onClick={handleUserInput}
                disabled={isLoadingResponse || !userInput.trim()}
                className={`ml-2 p-2 rounded-full ${
                  isLoadingResponse || !userInput.trim()
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-blue-500 hover:bg-blue-600'
                } transition-colors duration-200`}
              >
                <Send size={24} className="text-white" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
