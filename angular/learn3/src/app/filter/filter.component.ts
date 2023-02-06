import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-filter',
  templateUrl: './filter.component.html',
  styleUrls: ['./filter.component.css']
})
export class FilterComponent {

  //Decorated to be an input parameter (receiving stuff) //custom properly binding
  @Input('allCourses') all: number = 0;  //Now it is aliased, so in the parent you use the alias, you still use all in the internal class
  @Input() free: number = 0;
  @Input() premium: number = 0;

  selectedRadioButtonValue: string = 'free';

  //This is a custom event
  @Output()
  filterChanged: EventEmitter<string> = new EventEmitter<string>();

  //emit the value of the above variable above
  onRadioClick(){
    this.filterChanged.emit(this.selectedRadioButtonValue);
    console.log('Child ' + this.selectedRadioButtonValue)
  }

}
