import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { ChatService, ChatMessage, Session } from './chat.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  providers: [ChatService],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit, AfterViewChecked {
  @ViewChild('scrollMe') private myScrollContainer!: ElementRef;

  sessions: Session[] = [];
  currentSessionId: string | null = null;
  messages: ChatMessage[] = [];
  userInput: string = '';
  isLoading: boolean = false;

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    this.loadSessions();
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.myScrollContainer.nativeElement.scrollTop = this.myScrollContainer.nativeElement.scrollHeight;
    } catch(err) { }
  }

  loadSessions() {
    this.chatService.getSessions().subscribe(res => {
      this.sessions = res.sessions;
      if (this.sessions.length === 0) {
        this.createNewSession();
      } else {
        this.selectSession(this.sessions[0].session_id);
      }
    });
  }

  createNewSession() {
    this.chatService.createSession().subscribe(res => {
      this.currentSessionId = res.session_id;
      this.messages = [];
      this.loadSessions();
    });
  }

  selectSession(sessionId: string) {
    this.currentSessionId = sessionId;
    this.chatService.getHistory(sessionId).subscribe(res => {
      this.messages = res.messages;
    });
  }

  sendMessage() {
    if (!this.userInput.trim() || !this.currentSessionId || this.isLoading) return;

    const text = this.userInput;
    this.messages.push({ role: 'human', content: text });
    this.userInput = '';
    this.isLoading = true;

    this.chatService.sendMessage(this.currentSessionId, text).subscribe({
      next: (res) => {
        this.messages.push({ role: 'assistant', content: res.reply });
        this.isLoading = false;
      },
      error: (err) => {
        this.messages.push({ role: 'assistant', content: '❌ Error: Could not reach the AI agent.' });
        this.isLoading = false;
        console.error(err);
      }
    });
  }
}
