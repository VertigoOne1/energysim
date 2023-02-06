import { Component } from '@angular/core';

@Component({
  selector: 'app-search',
  templateUrl: './search.component.html',
  styleUrls: ['./search.component.css']
})
export class SearchComponent {

  searchValue: string = '';

  changesearchValue(eventData: Event) {
    console.log(eventData)
    console.log((<HTMLInputElement>eventData.target).value);
    this.searchValue = "aaa " + (<HTMLInputElement>eventData.target).value;
    console.log("aaa " + this.searchValue)
  }

}
