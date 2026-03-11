import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ChatMessage {
  role: 'human' | 'assistant';
  content: string;
}

export interface Session {
  session_id: string;
  last_active: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) { }

  getSessions(): Observable<{ sessions: Session[] }> {
    return this.http.get<{ sessions: Session[] }>(`${this.apiUrl}/sessions`);
  }

  createSession(): Observable<{ session_id: string }> {
    return this.http.post<{ session_id: string }>(`${this.apiUrl}/sessions`, {});
  }

  getHistory(sessionId: string): Observable<{ session_id: string, messages: ChatMessage[] }> {
    return this.http.get<{ session_id: string, messages: ChatMessage[] }>(`${this.apiUrl}/sessions/${sessionId}/history`);
  }

  sendMessage(sessionId: string, message: string): Observable<{ session_id: string, reply: string }> {
    return this.http.post<{ session_id: string, reply: string }>(`${this.apiUrl}/chat`, {
      session_id: sessionId,
      message: message
    });
  }
}
