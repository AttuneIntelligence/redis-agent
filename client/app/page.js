"use client";
import React, { useState, useEffect, useRef, useMemo } from "react";
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import Image from 'next/image';
import { Send, Loader2 } from 'lucide-react';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import Head from 'next/head';

// Memoized components for better performance
const MemoizedReactMarkdown = React.memo(ReactMarkdown);
const MemoizedSyntaxHighlighter = React.memo(SyntaxHighlighter);

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
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
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

  // Memoized markdown components for better performance
  const markdownComponents = useMemo(() => ({
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <MemoizedSyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
          {String(children).replace(/\n$/, '')}
        </MemoizedSyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    a: ({ children, href, ...props }) => {
      const isExternal = href && !href.startsWith('/') && !href.startsWith('#') && !href.includes('localhost');
      return isExternal ? (
        <a {...props} href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      ) : null;
    },
    p: ({ children }) => <p className="mb-2">{children}</p>,
    h1: ({ children }) => <h1 className="text-3xl font-bold mb-2">{children}</h1>,
    h2: ({ children }) => <h2 className="text-2xl font-bold mb-2">{children}</h2>,
    h3: ({ children }) => <h3 className="text-xl font-bold mb-2">{children}</h3>,
    h4: ({ children }) => <h4 className="text-lg font-bold mb-2">{children}</h4>,
    h5: ({ children }) => <h5 className="text-base font-bold mb-2">{children}</h5>,
    h6: ({ children }) => <h6 className="text-sm font-bold mb-2">{children}</h6>,
    sup: ({ children }) => <sup className="align-super">{children}</sup>,
    emoji: ({ children }) => <span className="emoji">{children}</span>,
  }), []);

  return (
    <>
      <Head>
        <title>Redis Agent</title>
      </Head>
      <div className="bg-gradient-to-b from-gray-100 to-gray-200 min-h-screen flex flex-col justify-center items-center p-4">
        <div className="w-full max-w-4xl bg-white rounded-lg shadow-xl overflow-hidden transition-shadow duration-300 hover:shadow-2xl">
          <div
            className="h-[calc(100vh-200px)] overflow-y-auto p-6 md:p-12 space-y-6"
            ref={chatContainerRef}
          >
            {chatHistory.map((message, index) => (
              <div
                key={index}
                className={`flex items-start ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start max-w-[80%]`}>
                  <div className="w-10 h-10 rounded-full flex-shrink-0 relative overflow-hidden">
                    <Image
                      src={message.role === 'user' ? '/user-image-icon.jpg' : '/ai_image.png'}
                      alt={`${message.role} profile`}
                      fill
                      className="rounded-full object-cover"
                      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    />
                  </div>
                  <div 
                    className={`mx-3 p-4 rounded-2xl ${
                      message.role === 'user' 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-gray-100 text-black'
                    } shadow-md`}
                  >
                    <MemoizedReactMarkdown
                      className="prose max-w-none"
                      components={markdownComponents}
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                    >
                      {message.content}
                    </MemoizedReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="border-t p-4 bg-gray-50">
            <div className="flex items-end">
              <textarea
                ref={textareaRef}
                placeholder="Ask me anything..."
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none text-black transition-all duration-200 ease-in-out"
                style={{ minHeight: '44px', maxHeight: '120px' }}
              />
              <button
                onClick={handleUserInput}
                disabled={isLoadingResponse || !userInput.trim()}
                className={`ml-3 p-3 rounded-full ${
                  isLoadingResponse || !userInput.trim()
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-blue-500 hover:bg-blue-600'
                } transition-all duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
              >
                {isLoadingResponse ? (
                  <Loader2 size={24} className="text-white animate-spin" />
                ) : (
                  <Send size={24} className="text-white" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}