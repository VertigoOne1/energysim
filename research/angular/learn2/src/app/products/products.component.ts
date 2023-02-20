import { Component } from '@angular/core';

@Component({
  selector: 'app-products',
  templateUrl: './products.component.html',
  styleUrls: ['./products.component.css']
})
export class ProductsComponent {

  products = [
    {id: 1, name: "bla1", price:'100', colour: "Black", available: "Yes"},
    {id: 2, name: "bla2", price:'150', colour: "White", available: "No"},
    {id: 3, name: "bla3", price:'160', colour: "Black", available: "Yes"},
    {id: 4, name: "bla4", price:'180', colour: "Green", available: "No"}
  ]

}
