import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-pickleball',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pickleball.component.html',
  styleUrl: './pickleball.component.scss'
})
export class PickleballComponent {
  @Output() navigate = new EventEmitter<void>();

  onNavigate() {
    this.navigate.emit();
  }
}
